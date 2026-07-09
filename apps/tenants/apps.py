# [Domínio: tenants] [Skill: app_config]
"""
📖 MANIFESTO (Estrutura de Diretórios):
"apps/tenants/ # Barbearias, Multi-tenancy (tenants_barbearia)"

📖 MANIFESTO (Rastreabilidade Obrigatória):
"Toda e qualquer resposta contendo código DEVE iniciar obrigatoriamente
com a etiqueta de identificação do domínio e skill correspondente no topo."

✅ Regras seguidas:
- Etiqueta de domínio e skill no topo
- AppConfig com verbose_name descritivo
- name segue padrão apps.tenants
"""

from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenants'
    verbose_name = "Tenants (Barbearias e Multi-Tenancy)"

