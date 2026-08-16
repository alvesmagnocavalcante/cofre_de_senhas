import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connections, transaction

from gerenciador.models import (
    AuditEvent,
    Membership,
    Organization,
    VaultGroup,
    VaultItem,
)
from gerenciador.security import encrypt_value


# Copia somente campos concretos, preservando chaves e datas.
def clone(model, source, **overrides):
    values = {field.attname: getattr(source, field.attname) for field in model._meta.concrete_fields}
    values.update(overrides)
    return model(**values)


class Command(BaseCommand):
    help = "Migra o SQLite legado para o PostgreSQL e rotaciona a criptografia."

    def handle(self, *args, **options):
        if "legacy" not in connections:
            raise CommandError("Defina LEGACY_SQLITE_PATH antes de executar.")
        if connections["default"].vendor != "postgresql":
            raise CommandError("O banco principal deve ser PostgreSQL.")

        legacy_secret = os.environ.get("LEGACY_DJANGO_SECRET_KEY")
        if not legacy_secret:
            raise CommandError("Defina LEGACY_DJANGO_SECRET_KEY.")
        legacy_key = base64.urlsafe_b64encode(
            hashlib.sha256(legacy_secret.encode()).digest()
        )
        legacy_cipher = Fernet(legacy_key)

        self._validate_source()
        decrypted_items = self._decrypt_items(legacy_cipher)
        self._validate_target()

        with transaction.atomic(using="default"):
            self._copy_data(decrypted_items)
            self._reset_sequences()

        self.stdout.write(
            self.style.SUCCESS(
                f"Migração concluída: {len(decrypted_items)} credencial(is) recriptografada(s)."
            )
        )

    def _validate_source(self):
        if Group.objects.using("legacy").exists():
            raise CommandError("O SQLite possui grupos de autenticação não suportados.")
        users = get_user_model().objects.using("legacy")
        if any(user.user_permissions.exists() or user.groups.exists() for user in users):
            raise CommandError("O SQLite possui permissões individuais não suportadas.")

    def _decrypt_items(self, cipher):
        decrypted = []
        try:
            for item in VaultItem.objects.using("legacy").all():
                secret = cipher.decrypt(bytes(item.secret_encrypted)).decode()
                notes = (
                    cipher.decrypt(bytes(item.notes_encrypted)).decode()
                    if item.notes_encrypted
                    else ""
                )
                decrypted.append((item, secret, notes))
        except InvalidToken as exc:
            raise CommandError(
                "A chave de desenvolvimento não decifra todas as credenciais."
            ) from exc
        return decrypted

    def _validate_target(self):
        models = (get_user_model(), Membership, VaultGroup, VaultItem, AuditEvent)
        if any(model.objects.using("default").exists() for model in models):
            raise CommandError("O PostgreSQL já possui dados; migração cancelada.")

    def _copy_data(self, decrypted_items):
        user_model = get_user_model()
        Organization.objects.using("default").all().delete()
        Organization.objects.using("default").bulk_create(
            [clone(Organization, row) for row in Organization.objects.using("legacy")]
        )
        user_model.objects.using("default").bulk_create(
            [clone(user_model, row) for row in user_model.objects.using("legacy")]
        )
        Membership.objects.using("default").bulk_create(
            [clone(Membership, row) for row in Membership.objects.using("legacy")]
        )
        VaultGroup.objects.using("default").bulk_create(
            [clone(VaultGroup, row) for row in VaultGroup.objects.using("legacy")]
        )

        items = [
            clone(
                VaultItem,
                item,
                secret_encrypted=encrypt_value(secret),
                notes_encrypted=encrypt_value(notes) if notes else b"",
            )
            for item, secret, notes in decrypted_items
        ]
        VaultItem.objects.using("default").bulk_create(items)
        AuditEvent.objects.using("default").bulk_create(
            [clone(AuditEvent, row) for row in AuditEvent.objects.using("legacy")]
        )

        shared_model = VaultItem.shared_with.through
        shared_model.objects.using("default").bulk_create(
            [
                shared_model(
                    vaultitem_id=row.vaultitem_id,
                    user_id=row.user_id,
                )
                for row in shared_model.objects.using("legacy").all()
            ]
        )

    def _reset_sequences(self):
        models = [get_user_model(), Membership, AuditEvent]
        sql = connections["default"].ops.sequence_reset_sql(no_style(), models)
        with connections["default"].cursor() as cursor:
            for statement in sql:
                cursor.execute(statement)
