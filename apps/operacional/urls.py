from django.urls import path
from apps.operacional.views import (
    # Serviços
    ServicoListView, ServicoCreateView, ServicoDetailView, ServicoUpdateView, ServicoToggleAtivoView,
    # Profissionais
    ProfissionalListView, ProfissionalCreateView, ProfissionalUpdateView, ProfissionalToggleAtivoView,
    # Grade Horária
    GradeHorariaListView, GradeHorariaCreateView, GradeHorariaUpdateView, GradeHorariaDeleteView,
    # Indisponibilidades
    DiaIndisponivelCreateView, DiaIndisponivelDeleteView,
    IntervaloIndisponivelCreateView, IntervaloIndisponivelDeleteView,
    # Habilitação
    ServicoProfissionalHabilitarView,
    ServicoProfissionaisListView, ServicoProfissionalToggleView,
    # Convites
    ConviteProfissionalCreateView, ConviteAceitarView,
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
    
    # ─────────────────────────────────────────────────────────
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
    path('grades/<int:grade_id>/', GradeHorariaUpdateView.as_view(), name='grade-update'),
    path('grades/<int:grade_id>/delete/', GradeHorariaDeleteView.as_view(), name='grade-delete'),

    # ─────────────────────────────────────────────────────────
    # INDISPONIBILIDADES
    # ─────────────────────────────────────────────────────────
    path('profissionais/<int:profissional_id>/dias-indisponiveis/', DiaIndisponivelCreateView.as_view(), name='dia-indisponivel-create'),
    path('dias-indisponiveis/<int:dia_id>/delete/', DiaIndisponivelDeleteView.as_view(), name='dia-indisponivel-delete'),
    path('profissionais/<int:profissional_id>/intervalos-indisponiveis/', IntervaloIndisponivelCreateView.as_view(), name='intervalo-indisponivel-create'),
    path('intervalos-indisponiveis/<int:intervalo_id>/delete/', IntervaloIndisponivelDeleteView.as_view(), name='intervalo-indisponivel-delete'),

    # ─────────────────────────────────────────────────────────
    # HABILITAÇÃO DE SERVIÇOS
    # ─────────────────────────────────────────────────────────
    path('servicos/habilitar/', ServicoProfissionalHabilitarView.as_view(), name='servico-habilitar'),
    path('servicos/<int:servico_id>/profissionais/', ServicoProfissionaisListView.as_view(), name='servico-profissionais-list'),
    path('servicos/<int:servico_id>/profissionais/<int:profissional_id>/toggle/', ServicoProfissionalToggleView.as_view(), name='servico-profissional-toggle'),

    # ─────────────────────────────────────────────────────────
    # CONVITES (Fluxo Híbrido)
    # ─────────────────────────────────────────────────────────
    path('convites/create/', ConviteProfissionalCreateView.as_view(), name='convite-create'),
    path('convites/aceitar/', ConviteAceitarView.as_view(), name='convite-aceitar'),
]

