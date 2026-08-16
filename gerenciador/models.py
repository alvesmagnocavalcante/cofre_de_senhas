import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from .security import decrypt_value, encrypt_value


# Validação comum aos objetos do cofre.
def _is_active_member(organization_id, user_id):
    return Membership.objects.filter(
        organization_id=organization_id,
        user_id=user_id,
        is_active=True,
    ).exists()


# Organização e controle de acesso.
class Organization(models.Model):
    id = models.UUIDField(
        "identificador", primary_key=True, default=uuid.uuid4, editable=False
    )
    name = models.CharField("nome", max_length=150)
    slug = models.SlugField("identificador curto", max_length=80, unique=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Proprietário"
        ADMIN = "admin", "Administrador"
        MEMBER = "member", "Membro"

    organization = models.ForeignKey(
        Organization,
        verbose_name="organização",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        "perfil", max_length=10, choices=Role.choices, default=Role.MEMBER
    )
    is_active = models.BooleanField("aprovado e ativo", default=True)
    created_at = models.DateTimeField("cadastrado em", auto_now_add=True)

    class Meta:
        verbose_name = "Cadastro de usuário"
        verbose_name_plural = "Cadastros de usuários"
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "user"), name="unique_org_member"
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.organization}"


# Agrupamento das credenciais.
class VaultGroup(models.Model):
    id = models.UUIDField(
        "identificador", primary_key=True, default=uuid.uuid4, editable=False
    )
    organization = models.ForeignKey(
        Organization,
        verbose_name="organização",
        on_delete=models.CASCADE,
        related_name="vault_groups",
    )
    name = models.CharField("nome", max_length=80)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criado por",
        on_delete=models.PROTECT,
        related_name="vault_groups",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Grupo de senhas"
        verbose_name_plural = "Grupos de senhas"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "organization", name="unique_group_name_per_org"
            ),
        ]

    def clean(self):
        if (
            self.created_by_id
            and self.organization_id
            and not _is_active_member(self.organization_id, self.created_by_id)
        ):
            raise ValidationError("O criador deve ser membro ativo da organização.")

    def __str__(self):
        return self.name


# Credenciais armazenadas com campos criptografados.
class VaultItem(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Somente eu"
        SPECIFIC = "specific", "Usuários específicos"
        ORGANIZATION = "organization", "Todos da Carmel"

    id = models.UUIDField(
        "identificador", primary_key=True, default=uuid.uuid4, editable=False
    )
    organization = models.ForeignKey(
        Organization,
        verbose_name="organização",
        on_delete=models.CASCADE,
        related_name="vault_items",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criada por",
        on_delete=models.PROTECT,
        related_name="vault_items",
    )
    group = models.ForeignKey(
        VaultGroup,
        verbose_name="grupo",
        on_delete=models.SET_NULL,
        related_name="vault_items",
        null=True,
        blank=True,
    )
    title = models.CharField("título", max_length=150)
    host = models.CharField("IP ou nome do equipamento", max_length=255, blank=True)
    username = models.CharField("usuário", max_length=254, blank=True)
    website = models.URLField("site", blank=True)
    secret_encrypted = models.BinaryField("senha criptografada", editable=False)
    notes_encrypted = models.BinaryField(
        "observações criptografadas", editable=False, blank=True, default=b""
    )
    visibility = models.CharField(
        "visibilidade",
        max_length=12,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="compartilhada com",
        related_name="shared_vault_items",
        blank=True,
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        verbose_name = "Senha do cofre"
        verbose_name_plural = "Senhas do cofre"
        ordering = ("title",)
        indexes = [
            models.Index(fields=("organization", "visibility")),
            models.Index(fields=("organization", "created_by")),
        ]

    def clean(self):
        if (
            self.created_by_id
            and self.organization_id
            and not _is_active_member(self.organization_id, self.created_by_id)
        ):
            raise ValidationError("O criador deve ser membro ativo da organização.")
        if (
            self.group_id
            and self.organization_id
            and self.group.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"group": "O grupo deve pertencer à mesma organização da senha."}
            )

    def set_secret(self, value):
        self.secret_encrypted = encrypt_value(value)

    def get_secret(self):
        return decrypt_value(self.secret_encrypted)

    def set_notes(self, value):
        self.notes_encrypted = encrypt_value(value) if value else b""

    def get_notes(self):
        return decrypt_value(self.notes_encrypted) if self.notes_encrypted else ""

    def __str__(self):
        return self.title


# Histórico das ações realizadas no sistema.
class AuditEvent(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Criou"
        UPDATE = "update", "Atualizou"
        DELETE = "delete", "Excluiu"
        REVEAL = "reveal", "Revelou"
        COPY = "copy", "Copiou"
        SHARE_UPDATE = "share_update", "Alterou compartilhamento"
        USER_APPROVE = "user_approve", "Aprovou usuário"
        USER_SUSPEND = "user_suspend", "Suspendeu usuário"
        USER_ROLE = "user_role", "Alterou perfil de usuário"
        USER_LOGOUT = "user_logout", "Encerrou sessões de usuário"
        USER_UNLOCK = "user_unlock", "Desbloqueou acesso de usuário"
        GROUP_UPDATE = "group_update", "Renomeou grupo"
        GROUP_DELETE = "group_delete", "Excluiu grupo"

    organization = models.ForeignKey(
        Organization,
        verbose_name="organização",
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário responsável",
        on_delete=models.PROTECT,
        related_name="vault_audit_events",
    )
    vault_item_id = models.UUIDField("identificador da senha", null=True, blank=True)
    item_title = models.CharField("título da senha", max_length=150)
    action = models.CharField("ação", max_length=20, choices=Action.choices)
    ip_address = models.GenericIPAddressField("endereço IP", null=True, blank=True)
    created_at = models.DateTimeField("realizado em", auto_now_add=True)

    class Meta:
        verbose_name = "Evento de auditoria"
        verbose_name_plural = "Eventos de auditoria"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("organization", "-created_at"))]
