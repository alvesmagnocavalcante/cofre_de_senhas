from axes.models import AccessAttempt
from django.db.models import Count, F, Q

from .models import AuditEvent, Membership, VaultGroup, VaultItem


# Consultas das credenciais visíveis.
def visible_items(user, organization):
    items = VaultItem.objects.filter(organization=organization)
    return items.filter(
        Q(created_by=user)
        | Q(visibility=VaultItem.Visibility.ORGANIZATION)
        | Q(visibility=VaultItem.Visibility.SPECIFIC, shared_with=user)
    ).distinct()


def search_items(items, query):
    if not query:
        return items
    return items.filter(
        Q(title__icontains=query)
        | Q(host__icontains=query)
        | Q(username__icontains=query)
        | Q(website__icontains=query)
        | Q(group__name__icontains=query)
    )


def ordered_items(items):
    return items.order_by(F("group__name").asc(nulls_first=True), "title")


# Dados consolidados do painel administrativo.
def dashboard_data(organization, user_query="", group_query=""):
    all_memberships = Membership.objects.filter(
        organization=organization
    ).select_related("user")
    memberships = all_memberships.order_by("is_active", "user__username")
    all_groups = (
        VaultGroup.objects.filter(organization=organization)
        .select_related("created_by")
        .annotate(
            total_items=Count("vault_items"),
            private_items=Count(
                "vault_items",
                filter=Q(vault_items__visibility=VaultItem.Visibility.PRIVATE),
            ),
            shared_items=Count(
                "vault_items",
                filter=~Q(vault_items__visibility=VaultItem.Visibility.PRIVATE),
            ),
        )
    )
    if user_query:
        memberships = memberships.filter(user__username__icontains=user_query)
    groups = (
        all_groups.filter(name__icontains=group_query) if group_query else all_groups
    )

    membership_list = list(memberships)
    failed_users = set(
        AccessAttempt.objects.filter(
            username__in=[member.user.username for member in membership_list],
        ).values_list("username", flat=True)
    )
    for membership in membership_list:
        membership.has_login_failures = membership.user.username in failed_users

    items = VaultItem.objects.filter(organization=organization)
    return {
        "memberships": membership_list,
        "groups": groups,
        "recent_events": AuditEvent.objects.filter(
            organization=organization
        ).select_related("actor")[:20],
        "stats": {
            "active_users": all_memberships.filter(
                is_active=True, user__is_active=True
            ).count(),
            "pending_users": all_memberships.filter(
                Q(is_active=False) | Q(user__is_active=False)
            ).count(),
            "groups": all_groups.count(),
            "items": items.count(),
            "shared_items": items.exclude(
                visibility=VaultItem.Visibility.PRIVATE
            ).count(),
        },
    }
