# [Domínio: tenants] [Skill: urls]
"""
📖 MANIFESTO (Estrutura de URLs):
"api/v1/tenants/barbearias/ # Endpoints de Barbearias"

✅ Regras seguidas:
- URLs organizadas por domínio
- Prefixo /api/v1/ para versionamento
- Nomes de URL descritivos (name=)
"""
from django.urls import path

from apps.tenants.views import (
    BarbeariaCreateView,
    BarbeariaDetailView,
    BarbeariaListView,
    BarbeariaProximidadeView,
    BarbeariaContextoListView,
    
)

app_name = 'tenants'

urlpatterns = [
    # POST /api/v1/tenants/barbearias/create/
    path('barbearias/create/', BarbeariaCreateView.as_view(), name='barbearia-create'),
    
    # GET /api/v1/tenants/barbearias/
    path('barbearias/', BarbeariaListView.as_view(), name='barbearia-list'),
    
    # GET /api/v1/tenants/barbearias/proximidade/
    path('barbearias/proximidade/', BarbeariaProximidadeView.as_view(), name='barbearia-proximidade'),
    
    # GET/PUT/DELETE /api/v1/tenants/barbearias/{barbearia_id}/
    path('barbearias/<uuid:barbearia_id>/', BarbeariaDetailView.as_view(), name='barbearia-detail'),

    # GET /api/v1/tenants/barbearias/meu-contexto/
    path('barbearias/meu-contexto/', BarbeariaContextoListView.as_view(), name='barbearia-meu-contexto'),

    # GET /api/v1/tenants/barbearias/meu-contexto/{barbearia_id}/
     path('barbearias/meu-contexto/',BarbeariaContextoListView.as_view(),name='barbearias-meu-contexto'
    ),
]

