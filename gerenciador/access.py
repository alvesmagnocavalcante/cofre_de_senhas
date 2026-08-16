from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render

from .constants import ORGANIZATION_SLUG
from .models import Membership


# Consulta e regra central de acesso.
def get_membership(user):
    return (
        Membership.objects.select_related("organization")
        .filter(
            user=user,
            organization__slug=ORGANIZATION_SLUG,
            is_active=True,
        )
        .first()
    )


def can_administer(user, membership):
    return bool(
        membership
        and (
            user.is_staff
            or membership.role in (Membership.Role.OWNER, Membership.Role.ADMIN)
        )
    )


# Decoradores das áreas autenticadas.
def membership_required(view=None, *, json_response=False):
    def decorator(view_function):
        @login_required
        @wraps(view_function)
        def wrapped(request, *args, **kwargs):
            membership = get_membership(request.user)
            if membership:
                return view_function(request, *args, membership=membership, **kwargs)
            if json_response:
                return JsonResponse({"error": "Organização indisponível."}, status=403)
            return render(request, "vault/no_organization.html", status=403)

        return wrapped

    return decorator(view) if view else decorator


def administrator_required(view_function):
    @login_required
    @wraps(view_function)
    def wrapped(request, *args, **kwargs):
        membership = get_membership(request.user)
        if not can_administer(request.user, membership):
            return HttpResponseForbidden(
                "Acesso permitido somente para administradores."
            )
        return view_function(request, *args, administrator=membership, **kwargs)

    return wrapped


def administrator_target_required(view_function):
    @administrator_required
    @wraps(view_function)
    def wrapped(request, membership_id, administrator, *args, **kwargs):
        target = get_object_or_404(
            Membership.objects.select_related("user"),
            pk=membership_id,
            organization=administrator.organization,
        )
        return view_function(
            request,
            *args,
            administrator=administrator,
            target=target,
            **kwargs,
        )

    return wrapped
