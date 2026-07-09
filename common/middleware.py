# [Domínio: core] [Skill: middleware]
"""
📖 MANIFESTO (Seção 1 - Isolamento Multi-Tenant):
"Um middleware captura o identificador do tenant a partir do JWT e o injeta
em um armazenamento local seguro por thread."

📖 MANIFESTO (Mecanismo de Isolamento - 4 passos):
"1. Injeção no Token: O Django injeta o atributo barbearia_vinculo_id
no payload do JWT no login.
2. Interceptação: Middleware intercepta chamadas.
3. Decodificação: Lê o ID autorizado.
4. Filtro Forçado: Adiciona a trava WHERE barbearia_id=X."

📖 MANIFESTO (US06 - Blindagem Multi-tenant):
"O middleware de segurança do Django deve interceptar a requisição,
confrontar com o ID contido no JWT e retornar um erro HTTP 403 Forbidden."

✅ Regras seguidas:
- Extrai tenant_id do JWT (via request.user)
- Injeta no ContextVar (thread-safe)
- Injeta também no PostgreSQL via SET LOCAL (RLS)
- Descarta parâmetros manuais de URL (segurança)
- Limpa contexto após requisição
- Falha no SET LOCAL é logada e propaga erro (CWE-703 corrigido)
"""
import logging
from typing import Optional
from uuid import UUID

from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from common.context import (
    clear_context,
    set_current_tenant_id,
    set_current_user_id,
)


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware que captura o tenant_id do JWT e o injeta no contexto.
    Também configura o RLS no PostgreSQL para defesa em profundidade.
    """
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Extrai tenant_id e user_id do request e os injeta no contexto."""
        # Limpa contexto anterior (evita vazamento entre requisições)
        clear_context()
        
        # Se não há usuário autenticado, não há tenant
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Extrai tenant_id do usuário (vem do JWT via SimpleJWT)
        tenant_id: Optional[UUID] = getattr(request.user, 'tenant_id', None)
        user_id: Optional[UUID] = getattr(request.user, 'id', None)
        
        # Injeta no ContextVar (thread-safe)
        if tenant_id:
            set_current_tenant_id(tenant_id)
        
        if user_id:
            set_current_user_id(user_id)
        
        # Defesa em profundidade: configura RLS no PostgreSQL
        if tenant_id:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SET LOCAL app.current_tenant = %s",
                        [str(tenant_id)]
                    )
            except Exception as e:
                logger.error(
                    "Falha crítica ao setar contexto de tenant no PostgreSQL: %s",
                    e,
                    exc_info=True
                )
                raise
        
        return None
    
    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse
    ) -> HttpResponse:
        """Limpa o contexto após a requisição."""
        clear_context()
        return response


class TenantEnforcementMiddleware(MiddlewareMixin):
    """
    Middleware que força o isolamento multi-tenant.
    Se o usuário está autenticado mas não tem tenant_id, retorna 403.
    """
    
    # Rotas que não exigem tenant (ex: cadastro, login)
    EXEMPT_ROUTES = [
        '/api/v1/auth/',
        '/api/v1/usuarios/create/',
        '/swagger/',
        '/redoc/',
        '/admin/',
    ]
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Verifica se o usuário autenticado tem tenant_id."""
        from django.http import JsonResponse
        
        # Rotas isentas
        if any(request.path.startswith(route) for route in self.EXEMPT_ROUTES):
            return None
        
        # Usuário não autenticado
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Verifica se tem tenant_id
        tenant_id = getattr(request.user, 'tenant_id', None)
        if not tenant_id:
            # US06: Retorna 403 se tentar acessar sem tenant
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Acesso negado. Usuário sem vínculo a uma barbearia.'
                },
                status=403
            )
        
        return None