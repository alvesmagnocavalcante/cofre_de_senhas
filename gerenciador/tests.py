from datetime import timedelta

from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import AuditEvent, Membership, Organization, VaultGroup, VaultItem


# Regras de segurança e autorização.
@override_settings(VAULT_ENCRYPTION_KEYS=Fernet.generate_key().decode())
class VaultSecurityTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            "alice", password="correct-horse-battery-staple"
        )
        self.bob = User.objects.create_user(
            "bob", password="correct-horse-battery-staple"
        )
        self.mallory = User.objects.create_user(
            "mallory", password="correct-horse-battery-staple"
        )
        self.org = Organization.objects.get(slug="carmel")
        self.other_org = Organization.objects.create(name="Other", slug="other")
        Membership.objects.filter(organization=self.org, user=self.alice).update(
            role=Membership.Role.OWNER
        )
        Membership.objects.filter(organization=self.org, user=self.mallory).delete()
        Membership.objects.create(
            organization=self.other_org, user=self.mallory, role=Membership.Role.OWNER
        )

    def make_item(
        self, owner=None, organization=None, shared=False, recipients=(), secret="S3gredo!"
    ):
        item = VaultItem(
            organization=organization or self.org,
            created_by=owner or self.alice,
            title="ERP",
            visibility=(
                VaultItem.Visibility.ORGANIZATION
                if shared
                else VaultItem.Visibility.SPECIFIC
                if recipients
                else VaultItem.Visibility.PRIVATE
            ),
        )
        item.set_secret(secret)
        item.set_notes("nota confidencial")
        item.full_clean()
        item.save()
        item.shared_with.set(recipients)
        return item

    def test_secret_and_notes_are_encrypted_at_rest(self):
        item = self.make_item(secret="texto-plano-proibido")
        item.refresh_from_db()
        self.assertNotIn(b"texto-plano-proibido", bytes(item.secret_encrypted))
        self.assertNotIn(b"nota confidencial", bytes(item.notes_encrypted))
        self.assertEqual(item.get_secret(), "texto-plano-proibido")
        self.assertEqual(item.get_notes(), "nota confidencial")

    def test_private_item_is_hidden_from_other_member(self):
        item = self.make_item(shared=False)
        self.client.force_login(self.bob)
        response = self.client.post(reverse("vault:reveal", args=[item.pk]))
        self.assertEqual(response.status_code, 404)

    def test_shared_item_can_be_revealed_and_is_audited(self):
        item = self.make_item(shared=True)
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("vault:reveal", args=[item.pk]), {"action": "copy"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["secret"], "S3gredo!")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.bob, action=AuditEvent.Action.COPY
            ).exists()
        )

    def test_shared_item_cannot_be_revealed_by_other_member(self):
        item = self.make_item(shared=True)
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("vault:reveal", args=[item.pk]), {"action": "reveal"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("secret", response.json())
        self.assertFalse(
            AuditEvent.objects.filter(
                actor=self.bob, action=AuditEvent.Action.REVEAL
            ).exists()
        )

    def test_specific_recipient_can_copy_item(self):
        item = self.make_item(recipients=(self.bob,))
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("vault:reveal", args=[item.pk]), {"action": "copy"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["secret"], "S3gredo!")

    def test_unselected_member_cannot_access_specific_item(self):
        item = self.make_item(recipients=(self.bob,))
        unselected = User.objects.create_user("charlie", password="senha-segura-2026")
        self.client.force_login(unselected)
        response = self.client.post(
            reverse("vault:reveal", args=[item.pk]), {"action": "copy"}
        )
        self.assertEqual(response.status_code, 404)

    def test_specific_sharing_requires_a_recipient(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("vault:create"),
            {
                "title": "Acesso específico",
                "secret": "senha-segura-2026",
                "visibility": VaultItem.Visibility.SPECIFIC,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione pelo menos um usuário.")
        self.assertFalse(VaultItem.objects.filter(title="Acesso específico").exists())

    def test_creator_can_share_with_specific_user(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("vault:create"),
            {
                "title": "Acesso selecionado",
                "secret": "senha-segura-2026",
                "visibility": VaultItem.Visibility.SPECIFIC,
                "shared_with": [self.bob.pk],
            },
        )
        self.assertRedirects(response, reverse("vault:list"))
        item = VaultItem.objects.get(title="Acesso selecionado")
        self.assertEqual(item.visibility, VaultItem.Visibility.SPECIFIC)
        self.assertEqual(list(item.shared_with.all()), [self.bob])

    def test_sharing_change_is_audited(self):
        item = self.make_item()
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("vault:update", args=[item.pk]),
            {
                "title": item.title,
                "secret": "",
                "visibility": VaultItem.Visibility.ORGANIZATION,
            },
        )
        self.assertRedirects(response, reverse("vault:list"))
        self.assertTrue(
            AuditEvent.objects.filter(
                vault_item_id=item.pk,
                action=AuditEvent.Action.SHARE_UPDATE,
                actor=self.alice,
            ).exists()
        )

    def test_user_without_carmel_membership_cannot_access_shared_item(self):
        item = self.make_item(shared=True)
        self.client.force_login(self.mallory)
        response = self.client.post(reverse("vault:reveal", args=[item.pk]))
        self.assertEqual(response.status_code, 403)

    def test_reveal_rejects_get(self):
        item = self.make_item(shared=True)
        self.client.force_login(self.alice)
        self.assertEqual(
            self.client.get(reverse("vault:reveal", args=[item.pk])).status_code, 405
        )

    def test_shared_item_cannot_be_edited_by_other_member(self):
        item = self.make_item(shared=True)
        self.client.force_login(self.bob)
        response = self.client.get(reverse("vault:update", args=[item.pk]))
        self.assertEqual(response.status_code, 404)

    def test_owner_cannot_access_another_users_private_item(self):
        item = self.make_item(owner=self.bob)
        self.client.force_login(self.alice)

        listing = self.client.get(reverse("vault:list"))
        self.assertNotContains(listing, item.title)
        reveal = self.client.post(
            reverse("vault:reveal", args=[item.pk]), {"action": "reveal"}
        )
        self.assertEqual(reveal.status_code, 404)
        copy = self.client.post(
            reverse("vault:reveal", args=[item.pk]), {"action": "copy"}
        )
        self.assertEqual(copy.status_code, 404)

        update = self.client.get(reverse("vault:update", args=[item.pk]))
        self.assertEqual(update.status_code, 404)

        delete = self.client.post(reverse("vault:delete", args=[item.pk]))
        self.assertEqual(delete.status_code, 404)
        self.assertTrue(VaultItem.objects.filter(pk=item.pk).exists())

    def test_superuser_django_admin_hides_another_users_private_item(self):
        item = self.make_item(owner=self.bob)
        self.alice.is_staff = True
        self.alice.is_superuser = True
        self.alice.save(update_fields=("is_staff", "is_superuser"))
        self.client.force_login(self.alice)

        listing = self.client.get(reverse("admin:gerenciador_vaultitem_changelist"))
        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(listing, item.title)

        change = self.client.get(
            reverse("admin:gerenciador_vaultitem_change", args=[item.pk])
        )
        self.assertNotEqual(change.status_code, 200)

        delete = self.client.post(
            reverse("admin:gerenciador_vaultitem_delete", args=[item.pk]),
            {"post": "yes"},
        )
        self.assertNotEqual(delete.status_code, 200)
        self.assertTrue(VaultItem.objects.filter(pk=item.pk).exists())

    def test_deleting_user_preserves_credentials_groups_and_audit(self):
        group = VaultGroup.objects.create(
            organization=self.org, created_by=self.bob, name="Grupo de Bob"
        )
        item = self.make_item(owner=self.bob)
        event = AuditEvent.objects.create(
            organization=self.org,
            actor=self.bob,
            vault_item_id=item.pk,
            item_title=item.title,
            action=AuditEvent.Action.CREATE,
        )

        self.bob.delete()

        group.refresh_from_db()
        item.refresh_from_db()
        event.refresh_from_db()
        self.assertIsNone(group.created_by)
        self.assertIsNone(item.created_by)
        self.assertIsNone(event.actor)

    def test_inactive_member_has_no_access(self):
        item = self.make_item(shared=True)
        Membership.objects.filter(organization=self.org, user=self.bob).update(
            is_active=False
        )
        self.client.force_login(self.bob)
        response = self.client.post(reverse("vault:reveal", args=[item.pk]))
        self.assertEqual(response.status_code, 403)

    def test_member_can_create_group(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("vault:group_create"), {"name": "Servidores"}
        )
        self.assertRedirects(response, reverse("vault:list"))
        self.assertTrue(
            VaultGroup.objects.filter(organization=self.org, name="Servidores").exists()
        )

    def test_only_group_creator_can_delete_it(self):
        group = VaultGroup.objects.create(
            organization=self.org, created_by=self.alice, name="Hosts"
        )
        self.client.force_login(self.bob)
        response = self.client.post(reverse("vault:group_delete", args=[group.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(VaultGroup.objects.filter(pk=group.pk).exists())

    def test_group_creator_can_rename_group_without_losing_items(self):
        group = VaultGroup.objects.create(
            organization=self.org, created_by=self.alice, name="Servidores antigos"
        )
        item = self.make_item()
        item.group = group
        item.save(update_fields=("group",))
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("vault:group_update", args=[group.pk]), {"name": "Servidores"}
        )
        self.assertRedirects(response, reverse("vault:list"))
        group.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(group.name, "Servidores")
        self.assertEqual(item.group, group)
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.GROUP_UPDATE, actor=self.alice
            ).exists()
        )

    def test_administration_panel_rejects_regular_member(self):
        self.client.force_login(self.bob)
        self.assertEqual(
            self.client.get(reverse("vault:administration")).status_code, 403
        )

    def test_owner_can_access_administration_and_approve_user(self):
        pending = User.objects.create_user(
            "aguardando", password="senha-pendente", is_active=False
        )
        pending_membership = Membership.objects.get(user=pending, organization=self.org)
        self.client.force_login(self.alice)
        dashboard = self.client.get(reverse("vault:administration"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertNotContains(dashboard, ">Desbloquear<")
        response = self.client.post(
            reverse("vault:administration_approve_user", args=[pending_membership.pk])
        )
        self.assertRedirects(response, reverse("vault:administration"))
        pending.refresh_from_db()
        pending_membership.refresh_from_db()
        self.assertTrue(pending.is_active)
        self.assertTrue(pending_membership.is_active)
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.USER_APPROVE, actor=self.alice
            ).exists()
        )

    def test_owner_can_promote_member_to_administrator(self):
        bob_membership = Membership.objects.get(user=self.bob, organization=self.org)
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("vault:administration_change_role", args=[bob_membership.pk]),
            {"role": Membership.Role.ADMIN},
        )
        self.assertRedirects(response, reverse("vault:administration"))
        bob_membership.refresh_from_db()
        self.assertEqual(bob_membership.role, Membership.Role.ADMIN)
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.USER_ROLE, actor=self.alice
            ).exists()
        )

    def test_regular_member_cannot_change_roles(self):
        alice_membership = Membership.objects.get(
            user=self.alice, organization=self.org
        )
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("vault:administration_change_role", args=[alice_membership.pk]),
            {"role": Membership.Role.MEMBER},
        )
        self.assertEqual(response.status_code, 403)
        alice_membership.refresh_from_db()
        self.assertEqual(alice_membership.role, Membership.Role.OWNER)

    def test_owner_can_end_another_users_sessions(self):
        other_client = Client()
        other_client.force_login(self.bob)
        bob_membership = Membership.objects.get(user=self.bob, organization=self.org)
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("vault:administration_end_sessions", args=[bob_membership.pk])
        )
        self.assertRedirects(response, reverse("vault:administration"))
        self.assertNotIn("_auth_user_id", other_client.session)
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.USER_LOGOUT, actor=self.alice
            ).exists()
        )

    def test_can_create_password_inside_group(self):
        group = VaultGroup.objects.create(
            organization=self.org, created_by=self.alice, name="Windows"
        )
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("vault:create"),
            {
                "group": group.pk,
                "title": "Servidor de arquivos",
                "host": "10.0.0.10",
                "username": "administrador",
                "website": "",
                "secret": "senha-segura-2026",
                "notes": "",
                "visibility": VaultItem.Visibility.PRIVATE,
            },
        )
        self.assertRedirects(response, reverse("vault:list"))
        item = VaultItem.objects.get(title="Servidor de arquivos")
        self.assertEqual(item.group, group)
        self.assertEqual(item.host, "10.0.0.10")
        self.assertEqual(item.get_secret(), "senha-segura-2026")


# Cadastro e aprovação de usuários.
class SignUpTests(TestCase):
    def test_login_page_has_theme_control(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "data-theme-toggle")
        self.assertContains(response, "Modo escuro")
        self.assertContains(response, "fonts.googleapis.com")

    def test_signup_shows_only_essential_guidance(self):
        response = self.client.get(reverse("vault:signup"))
        self.assertContains(response, "Até 150 caracteres")
        self.assertContains(response, "Use ao menos 8 caracteres")
        self.assertNotContains(response, "Sua senha não pode")

    def test_signup_creates_inactive_user_pending_approval(self):
        response = self.client.post(
            reverse("vault:signup"),
            {
                "username": "owner",
                "password1": "uma-senha-longa-e-unica-2026",
                "password2": "uma-senha-longa-e-unica-2026",
            },
        )
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(User.objects.get(username="owner").is_active)
        self.assertTrue(
            Membership.objects.filter(
                user__username="owner",
                organization__slug="carmel",
                role=Membership.Role.MEMBER,
                is_active=False,
            ).exists()
        )

    def test_admin_action_approves_pending_registration(self):
        pending_user = User.objects.create_user(
            "pending", password="senha-pendente-segura", is_active=False
        )
        membership = Membership.objects.get(
            user=pending_user, organization__slug="carmel"
        )
        self.assertFalse(membership.is_active)
        administrator = User.objects.create_superuser(
            "administrator", password="senha-admin-segura"
        )
        self.client.force_login(administrator)
        response = self.client.post(
            reverse("admin:gerenciador_membership_changelist"),
            {
                "action": "approve_members",
                "_selected_action": [membership.pk],
            },
        )
        self.assertEqual(response.status_code, 302)
        pending_user.refresh_from_db()
        membership.refresh_from_db()
        self.assertTrue(pending_user.is_active)
        self.assertTrue(membership.is_active)


# Bloqueio por tentativas inválidas de login.
@override_settings(AXES_FAILURE_LIMIT=2, AXES_COOLOFF_TIME=timedelta(minutes=15))
class LoginRateLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("target", password="senha-correta-segura")

    def test_login_is_blocked_after_repeated_failures(self):
        url = reverse("login")
        self.client.post(
            url,
            {"username": "target", "password": "incorreta"},
            REMOTE_ADDR="10.0.0.50",
        )
        response = self.client.post(
            url,
            {"username": "target", "password": "incorreta"},
            REMOTE_ADDR="10.0.0.50",
        )
        self.assertEqual(response.status_code, 429)
        self.assertContains(
            response, "Acesso temporariamente bloqueado", status_code=429
        )
        self.assertContains(response, "Tente novamente em 15 minutos", status_code=429)
