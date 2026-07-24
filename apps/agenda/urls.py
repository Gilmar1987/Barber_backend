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
from apps.agenda.views import (
    DisponibilidadeView, 
    AgendamentoCreateView, 
    MeusAgendamentosView, 
    AgendamentoClienteDeleteView
)

app_name = 'agenda'

urlpatterns = [
    path('disponibilidade/', DisponibilidadeView.as_view(), name='disponibilidade'),
    path('agendamentos/', AgendamentoCreateView.as_view(), name='agendamento-create'),
    path('meus-agendamentos/', MeusAgendamentosView.as_view(), name='meus-agendamentos'),
    path('agendamentos/<uuid:agendamento_id>/', AgendamentoClienteDeleteView.as_view(), name='agendamento-delete'),
]
