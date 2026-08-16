from django.apps import AppConfig


class GerenciadorConfig(AppConfig):
    name = "gerenciador"
    verbose_name = "Gerenciador de senhas"

    def ready(self):
        from . import signals  # noqa: F401
