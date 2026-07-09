# [Domínio: core] [Skill: app_config]
"""
📖 MANIFESTO (Estrutura de Diretórios):
"apps/core/ # Usuários, Auth, Vínculos (core_usuario, core_vinculo)"

✅ Regras seguidas:
- AppConfig com verbose_name descritivo
- name segue padrão apps.core
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = "Core (Usuários, Auth e Vínculos)"
    
    def ready(self) -> None:
        """Registra handlers de eventos quando o app é carregado."""
        # Importa handlers para registrá-los
        import apps.core.handlers  # noqa: F401