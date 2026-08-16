from django.contrib import admin
from django.urls import include, path

# Rotas gerais do projeto.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("conta/", include("django.contrib.auth.urls")),
    path("", include("gerenciador.urls")),
]
