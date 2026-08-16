from django.urls import path

from . import views

app_name = "vault"

# Rotas do cofre e do painel administrativo.
urlpatterns = [
    path("", views.vault_list, name="list"),
    path("cadastro/", views.signup, name="signup"),
    path("senhas/nova/", views.vault_create, name="create"),
    path("senhas/<uuid:item_id>/editar/", views.vault_update, name="update"),
    path("senhas/<uuid:item_id>/excluir/", views.vault_delete, name="delete"),
    path("senhas/<uuid:item_id>/revelar/", views.vault_reveal, name="reveal"),
    path("grupos/novo/", views.group_create, name="group_create"),
    path("grupos/<uuid:group_id>/editar/", views.group_update, name="group_update"),
    path("grupos/<uuid:group_id>/excluir/", views.group_delete, name="group_delete"),
    path("painel/", views.administration_dashboard, name="administration"),
    path(
        "painel/usuarios/<int:membership_id>/aprovar/",
        views.administration_approve_user,
        name="administration_approve_user",
    ),
    path(
        "painel/usuarios/<int:membership_id>/suspender/",
        views.administration_suspend_user,
        name="administration_suspend_user",
    ),
    path(
        "painel/usuarios/<int:membership_id>/perfil/",
        views.administration_change_role,
        name="administration_change_role",
    ),
    path(
        "painel/usuarios/<int:membership_id>/encerrar-sessoes/",
        views.administration_end_sessions,
        name="administration_end_sessions",
    ),
    path(
        "painel/usuarios/<int:membership_id>/desbloquear/",
        views.administration_unlock_user,
        name="administration_unlock_user",
    ),
]
