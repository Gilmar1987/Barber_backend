# [Domínio: agenda] [Skill: urls]
"""
📖 MANIFESTO (Estrutura de URLs):
"api/v1/tenants/barbearias/ # Endpoints de Barbearias"

✅ Regras seguidas:
- URLs organizadas por domínio
- Prefixo /api/v1/ para versionamento
- Nomes de URL descritivos (name=)
"""
from django.urls import path
from apps.agenda.views import DisponibilidadeView, AgendamentoCreateView

app_name = 'agenda'

urlpatterns = [
    path('disponibilidade/', DisponibilidadeView.as_view(), name='disponibilidade'),
    path('agendamentos/', AgendamentoCreateView.as_view(), name='agendamento-create'),
]
