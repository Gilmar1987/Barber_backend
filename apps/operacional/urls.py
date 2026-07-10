# [Domínio: operacional] [Skill: urls]
"""
📖 MANIFESTO (Estrutura de URLs):
"api/v1/operacional/servicos/ # Endpoints de Serviços"
"api/v1/operacional/profissionais/ # Endpoints de Profissionais"

✅ Regras seguidas:
- URLs organizadas por domínio
- Prefixo /api/v1/ para versionamento
- Nomes de URL descritivos (name=)
"""
from django.urls import path

from apps.operacional.views import (
    ProfissionalCreateView,
    ProfissionalListView,
    ProfissionalToggleAtivoView,
    ProfissionalUpdateView,
    ServicoCreateView,
    ServicoDetailView,
    ServicoListView,
    ServicoToggleAtivoView,
    ServicoUpdateView,
)

app_name = 'operacional'

urlpatterns = [
    # ─────────────────────────────────────────────────────────
    # SERVIÇOS
    # ─────────────────────────────────────────────────────────
    path('servicos/', ServicoListView.as_view(), name='servico-list'),
    path('servicos/create/', ServicoCreateView.as_view(), name='servico-create'),
    path('servicos/<int:servico_id>/', ServicoDetailView.as_view(), name='servico-detail'),
    path('servicos/<int:servico_id>/update/', ServicoUpdateView.as_view(), name='servico-update'),
    path('servicos/<int:servico_id>/toggle/', ServicoToggleAtivoView.as_view(), name='servico-toggle'),
    
    # ────────────────────────────────────────────────────────
    # PROFISSIONAIS
    # ─────────────────────────────────────────────────────────
    path('profissionais/', ProfissionalListView.as_view(), name='profissional-list'),
    path('profissionais/create/', ProfissionalCreateView.as_view(), name='profissional-create'),
    path('profissionais/<int:profissional_id>/update/', ProfissionalUpdateView.as_view(), name='profissional-update'),
    path('profissionais/<int:profissional_id>/toggle/', ProfissionalToggleAtivoView.as_view(), name='profissional-toggle'),
]