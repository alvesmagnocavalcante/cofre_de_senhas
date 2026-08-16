from django.contrib import admin

from .constants import ORGANIZATION_SLUG
from .models import AuditEvent, Membership, Organization, VaultGroup, VaultItem
from .services import set_memberships_active

admin.site.site_header = "Administração do Cofre Carmel"
admin.site.site_title = "Cofre Carmel"
admin.site.index_title = "Painel administrativo"


# Administração dos usuários.
class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_active", "created_at")
    list_filter = ("is_active", "role", "organization")
    search_fields = ("user__username",)
    actions = ("approve_members", "suspend_members")

    def _set_active(self, request, queryset, active, message):
        memberships = queryset.filter(organization__slug=ORGANIZATION_SLUG)
        updated = set_memberships_active(memberships, active)
        self.message_user(request, message.format(updated=updated))

    @admin.action(description="Aprovar cadastros selecionados")
    def approve_members(self, request, queryset):
        self._set_active(request, queryset, True, "{updated} cadastro(s) aprovado(s).")

    @admin.action(description="Suspender acessos selecionados")
    def suspend_members(self, request, queryset):
        self._set_active(request, queryset, False, "{updated} acesso(s) suspenso(s).")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Cadastros principais do cofre.
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    inlines = (MembershipInline,)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(VaultItem)
class VaultItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "group",
        "host",
        "organization",
        "created_by",
        "visibility",
        "updated_at",
    )
    list_filter = ("organization", "visibility")
    search_fields = ("title", "username")
    filter_horizontal = ("shared_with",)
    readonly_fields = (
        "secret_encrypted",
        "notes_encrypted",
        "created_at",
        "updated_at",
    )


@admin.register(VaultGroup)
class VaultGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "created_by", "created_at")
    list_filter = ("organization",)
    search_fields = ("name",)


# Auditoria disponível somente para leitura.
@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "organization",
        "actor",
        "action",
        "item_title",
        "ip_address",
    )
    list_filter = ("organization", "action")
    search_fields = ("item_title", "actor__username")
    audit_fields = tuple(field.name for field in AuditEvent._meta.fields)

    def get_readonly_fields(self, request, obj=None):
        return () if request.user.is_superuser else self.audit_fields

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
