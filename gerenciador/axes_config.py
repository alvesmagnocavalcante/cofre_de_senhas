from axes.apps import AppConfig as AxesAppConfig


# Traduz os modelos do controle de tentativas.
class AxesPortugueseConfig(AxesAppConfig):
    verbose_name = "Segurança de acesso"

    def ready(self):
        super().ready()
        from axes.models import (
            AccessAttempt,
            AccessAttemptExpiration,
            AccessFailureLog,
            AccessLog,
        )

        common_fields = {
            "user_agent": "Navegador e dispositivo",
            "ip_address": "Endereço IP",
            "username": "Usuário",
            "http_accept": "Formato HTTP aceito",
            "path_info": "Endereço acessado",
            "attempt_time": "Data da tentativa",
        }
        translations = {
            AccessAttempt: (
                "Tentativa de acesso",
                "Tentativas de acesso",
                common_fields
                | {
                    "get_data": "Dados da consulta",
                    "post_data": "Dados enviados",
                    "failures_since_start": "Falhas acumuladas",
                },
            ),
            AccessFailureLog: (
                "Falha de acesso",
                "Falhas de acesso",
                common_fields
                | {
                    "locked_out": "Acesso bloqueado",
                },
            ),
            AccessLog: (
                "Registro de acesso",
                "Registros de acesso",
                common_fields
                | {
                    "attempt_time": "Data de entrada",
                    "logout_time": "Data de saída",
                    "session_hash": "Identificador da sessão",
                },
            ),
            AccessAttemptExpiration: (
                "Expiração de tentativa de acesso",
                "Expirações de tentativas de acesso",
                {},
            ),
        }
        for model, (singular, plural, fields) in translations.items():
            model._meta.verbose_name = singular
            model._meta.verbose_name_plural = plural
            for field_name, label in fields.items():
                model._meta.get_field(field_name).verbose_name = label
