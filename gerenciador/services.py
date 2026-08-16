from axes.utils import reset as reset_login_attempts
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction

from .models import AuditEvent


# Registro central das ações de auditoria.
def record_audit(
    request, action, *, item=None, organization=None, target_id=None, title=None
):
    if item:
        organization, target_id, title = item.organization, item.pk, item.title
    return AuditEvent.objects.create(
        organization=organization,
        actor=request.user,
        vault_item_id=target_id,
        item_title=title,
        action=action,
        ip_address=request.META.get("REMOTE_ADDR") or None,
    )


# Ativação e suspensão de usuários.
@transaction.atomic
def set_membership_active(membership, active):
    membership.user.is_active = active
    membership.user.save(update_fields=("is_active",))
    membership.is_active = active
    membership.save(update_fields=("is_active",))


@transaction.atomic
def set_memberships_active(memberships, active):
    user_ids = list(memberships.values_list("user_id", flat=True))
    get_user_model().objects.filter(pk__in=user_ids).update(is_active=active)
    return memberships.update(is_active=active)


# Controle de sessões e bloqueios de login.
def end_user_sessions(user_id):
    sessions = [
        session.pk
        for session in Session.objects.all().iterator()
        if session.get_decoded().get("_auth_user_id") == str(user_id)
    ]
    return Session.objects.filter(pk__in=sessions).delete()[0]


def unlock_user(username):
    return reset_login_attempts(username=username)
