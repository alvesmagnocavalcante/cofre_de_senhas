from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .access import (
    administrator_required,
    administrator_target_required,
    can_administer,
    membership_required,
)
from .constants import ORGANIZATION_SLUG
from .forms import SignUpForm, VaultGroupForm, VaultItemForm
from .models import AuditEvent, Membership, Organization, VaultGroup, VaultItem
from .queries import dashboard_data, ordered_items, search_items, visible_items
from .services import (
    end_user_sessions,
    record_audit,
    set_membership_active,
    unlock_user,
)


# Funções auxiliares das rotas.
def _editable_group(request, membership, group_id):
    groups = VaultGroup.objects.filter(
        pk=group_id, organization=membership.organization
    )
    if not can_administer(request.user, membership):
        groups = groups.filter(created_by=request.user)
    return get_object_or_404(groups)


def _group_destination(request):
    returns_to_panel = (
        request.GET.get("retorno") == "painel"
        or request.POST.get("retorno") == "painel"
    )
    return "vault:administration" if returns_to_panel else "vault:list"


def _record_user_action(request, administrator, target, action, details=""):
    suffix = f"; {details}" if details else ""
    record_audit(
        request,
        action,
        organization=administrator.organization,
        title=f"Usuário: {target.user.username}{suffix}",
    )


# Cadastro público sujeito à aprovação.
def signup(request):
    if request.user.is_authenticated:
        return redirect("vault:list")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            Membership.objects.update_or_create(
                organization=Organization.objects.get(slug=ORGANIZATION_SLUG),
                user=user,
                defaults={"is_active": False},
            )
        messages.success(
            request, "Cadastro enviado. Aguarde a aprovação de um administrador."
        )
        return redirect("login")
    return render(request, "registration/signup.html", {"form": form})


# Operações das credenciais do cofre.
@membership_required
def vault_list(request, membership):
    query = request.GET.get("q", "").strip()
    items = (
        visible_items(request.user, membership.organization)
        .select_related("created_by", "group")
        .prefetch_related("shared_with")
    )
    return render(
        request,
        "vault/list.html",
        {
            "items": ordered_items(search_items(items, query)),
            "groups": VaultGroup.objects.filter(
                organization=membership.organization
            ).select_related("created_by"),
            "membership": membership,
            "query": query,
        },
    )


@membership_required
def vault_create(request, membership):
    form = VaultItemForm(
        request.POST or None,
        organization=membership.organization,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.organization = membership.organization
        item.created_by = request.user
        item.full_clean()
        item.save()
        form.save_m2m()
        record_audit(request, AuditEvent.Action.CREATE, item=item)
        messages.success(request, "Senha adicionada ao cofre.")
        return redirect("vault:list")
    return render(request, "vault/form.html", {"form": form, "title": "Nova senha"})


@membership_required
def vault_update(request, item_id, membership):
    item = get_object_or_404(
        VaultItem,
        pk=item_id,
        organization=membership.organization,
        created_by=request.user,
    )
    previous_sharing = (
        item.visibility,
        frozenset(item.shared_with.values_list("pk", flat=True)),
    )
    form = VaultItemForm(
        request.POST or None,
        instance=item,
        organization=membership.organization,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        item = form.save()
        record_audit(request, AuditEvent.Action.UPDATE, item=item)
        current_sharing = (
            item.visibility,
            frozenset(item.shared_with.values_list("pk", flat=True)),
        )
        if current_sharing != previous_sharing:
            record_audit(request, AuditEvent.Action.SHARE_UPDATE, item=item)
        messages.success(request, "Senha atualizada.")
        return redirect("vault:list")
    return render(
        request,
        "vault/form.html",
        {"form": form, "title": "Editar senha", "item": item},
    )


@membership_required
@require_POST
def vault_delete(request, item_id, membership):
    item = get_object_or_404(
        VaultItem,
        pk=item_id,
        organization=membership.organization,
        created_by=request.user,
    )
    record_audit(request, AuditEvent.Action.DELETE, item=item)
    item.delete()
    messages.success(request, "Senha excluída.")
    return redirect("vault:list")


@membership_required(json_response=True)
@require_POST
@never_cache
def vault_reveal(request, item_id, membership):
    item = get_object_or_404(
        visible_items(request.user, membership.organization), pk=item_id
    )
    action = request.POST.get("action", "reveal")
    if action == "reveal" and item.created_by_id != request.user.id:
        return JsonResponse(
            {"error": "Somente o criador pode visualizar esta senha."}, status=403
        )
    if action not in {"copy", "reveal"}:
        return JsonResponse({"error": "Ação inválida."}, status=400)

    audit_action = (
        AuditEvent.Action.COPY if action == "copy" else AuditEvent.Action.REVEAL
    )
    record_audit(request, audit_action, item=item)
    response = JsonResponse({"secret": item.get_secret()})
    response["Cache-Control"] = "no-store, private"
    response["Pragma"] = "no-cache"
    return response


# Criação, edição e exclusão de grupos.
@membership_required
def group_create(request, membership):
    form = VaultGroupForm(request.POST or None, organization=membership.organization)
    if request.method == "POST" and form.is_valid():
        group = form.save(commit=False)
        group.organization = membership.organization
        group.created_by = request.user
        group.full_clean()
        group.save()
        messages.success(request, "Grupo criado.")
        return redirect("vault:list")
    return render(request, "vault/form.html", {"form": form, "title": "Novo grupo"})


@membership_required
def group_update(request, group_id, membership):
    group = _editable_group(request, membership, group_id)
    old_name = group.name
    form = VaultGroupForm(
        request.POST or None, instance=group, organization=membership.organization
    )
    if request.method == "POST" and form.is_valid():
        group = form.save()
        record_audit(
            request,
            AuditEvent.Action.GROUP_UPDATE,
            organization=membership.organization,
            target_id=group.pk,
            title=f"Grupo: {old_name} → {group.name}",
        )
        messages.success(request, "Nome do grupo atualizado.")
        return redirect(_group_destination(request))
    return render(
        request,
        "vault/form.html",
        {
            "form": form,
            "title": "Editar grupo",
            "item": group,
            "cancel_url": reverse(_group_destination(request)),
        },
    )


@membership_required
@require_POST
def group_delete(request, group_id, membership):
    group = _editable_group(request, membership, group_id)
    group_id, group_name = group.pk, group.name
    group.delete()
    record_audit(
        request,
        AuditEvent.Action.GROUP_DELETE,
        organization=membership.organization,
        target_id=group_id,
        title=f"Grupo: {group_name}",
    )
    messages.success(request, "Grupo excluído. As senhas foram mantidas sem grupo.")
    return redirect(_group_destination(request))


# Operações do painel administrativo.
@administrator_required
def administration_dashboard(request, administrator):
    user_query = request.GET.get("usuario", "").strip()
    group_query = request.GET.get("grupo", "").strip()
    context = dashboard_data(administrator.organization, user_query, group_query)
    context.update(
        {
            "membership": administrator,
            "user_query": user_query,
            "group_query": group_query,
        }
    )
    return render(request, "administration/dashboard.html", context)


@administrator_target_required
@require_POST
def administration_approve_user(request, administrator, target):
    set_membership_active(target, True)
    _record_user_action(request, administrator, target, AuditEvent.Action.USER_APPROVE)
    messages.success(request, f"Cadastro de {target.user.username} aprovado.")
    return redirect("vault:administration")


@administrator_target_required
@require_POST
def administration_suspend_user(request, administrator, target):
    if target.user_id == request.user.id:
        messages.error(request, "Você não pode suspender o próprio acesso.")
        return redirect("vault:administration")
    set_membership_active(target, False)
    _record_user_action(request, administrator, target, AuditEvent.Action.USER_SUSPEND)
    messages.success(request, f"Acesso de {target.user.username} suspenso.")
    return redirect("vault:administration")


@administrator_target_required
@require_POST
def administration_change_role(request, administrator, target):
    new_role = request.POST.get("role")
    invalid = (
        target.user_id == request.user.id
        or target.role == Membership.Role.OWNER
        or new_role not in {Membership.Role.MEMBER, Membership.Role.ADMIN}
    )
    if invalid:
        messages.error(request, "Este perfil não pode ser alterado por esta operação.")
        return redirect("vault:administration")

    old_role = target.get_role_display()
    target.role = new_role
    target.save(update_fields=("role",))
    _record_user_action(
        request,
        administrator,
        target,
        AuditEvent.Action.USER_ROLE,
        f"{old_role} → {target.get_role_display()}",
    )
    messages.success(request, f"Perfil de {target.user.username} atualizado.")
    return redirect("vault:administration")


@administrator_target_required
@require_POST
def administration_end_sessions(request, administrator, target):
    if target.user_id == request.user.id:
        messages.error(
            request, "Você não pode encerrar a própria sessão por este painel."
        )
        return redirect("vault:administration")
    deleted = end_user_sessions(target.user_id)
    _record_user_action(
        request,
        administrator,
        target,
        AuditEvent.Action.USER_LOGOUT,
        f"sessões encerradas: {deleted}",
    )
    messages.success(
        request, f"{deleted} sessão(ões) de {target.user.username} encerrada(s)."
    )
    return redirect("vault:administration")


@administrator_target_required
@require_POST
def administration_unlock_user(request, administrator, target):
    removed = unlock_user(target.user.username)
    _record_user_action(
        request,
        administrator,
        target,
        AuditEvent.Action.USER_UNLOCK,
        f"bloqueios removidos: {removed}",
    )
    messages.success(request, f"Bloqueio de login de {target.user.username} removido.")
    return redirect("vault:administration")
