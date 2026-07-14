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
    GradeHorariaCreateView,
    GradeHorariaListView,
    DiaIndisponivelCreateView,
    IntervaloIndisponivelCreateView,
    ConviteProfissionalCreateView,
    ConviteAceitarView,
    ServicoProfissionalHabilitarView,
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



    # ─────────────────────────────────────────────────────────
    # GRADE HORÁRIA
    # ─────────────────────────────────────────────────────────
    path('profissionais/<int:profissional_id>/grades/', GradeHorariaListView.as_view(), name='grade-list'),
    path('profissionais/<int:profissional_id>/grades/create/', GradeHorariaCreateView.as_view(), name='grade-create'),

    # ─────────────────────────────────────────────────────────
    # INDISPONIBILIDADES
    # ─────────────────────────────────────────────────────────
    path('profissionais/<int:profissional_id>/dias-indisponiveis/', DiaIndisponivelCreateView.as_view(), name='dia-indisponivel-create'),
    path('profissionais/<int:profissional_id>/intervalos-indisponiveis/', IntervaloIndisponivelCreateView.as_view(), name='intervalo-indisponivel-create'),

    # ─────────────────────────────────────────────────────────
    # HABILITAÇÃO DE SERVIÇOS
    # ─────────────────────────────────────────────────────────
    path('servicos/habilitar/', ServicoProfissionalHabilitarView.as_view(), name='servico-habilitar'),

    # ─────────────────────────────────────────────────────────
    # CONVITES (Fluxo Híbrido)
    # ─────────────────────────────────────────────────────────
    path('convites/create/', ConviteProfissionalCreateView.as_view(), name='convite-create'),
    path('convites/aceitar/', ConviteAceitarView.as_view(), name='convite-aceitar'),

]


