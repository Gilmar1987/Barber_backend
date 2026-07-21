# [Domínio: core] [Skill: urls]
"""
📖 MANIFESTO (Tech Stack):
"Versionamento de API: Rotas explícitas sob escopo /api/v1/"

✅ Regras seguidas:
- Rotas sob /api/v1/ (versionamento)
- Nomes de URL descritivos
- Usa UUID em parâmetros de rota
"""
from django.urls import path

from apps.core.views import (
    UsuarioCreateView,
    UsuarioDetailView,
    UsuarioListView,
    UsuarioMeView,
    SelecionarTenantView,
)

app_name = 'core'

urlpatterns = [
    path(
        'usuarios/',
        UsuarioListView.as_view(),
        name='usuario-list'
    ),
    path(
        'usuarios/me/',
        UsuarioMeView.as_view(),
        name='usuario-me'
    ),
    path(
        'usuarios/create/',
        UsuarioCreateView.as_view(),
        name='usuario-create'
    ),
    path(
        'usuarios/<uuid:user_id>/',
        UsuarioDetailView.as_view(),
        name='usuario-detail'
    ),
    path(
        'auth/selecionar-tenant/',
        SelecionarTenantView.as_view(),
        name='selecionar-tenant'
    ),
]
