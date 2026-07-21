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

from django.db import DatabaseError, OperationalError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from common.context import (
    clear_context,
    set_current_tenant_id,
    set_current_user_id,
)


logger = logging.getLogger(__name__)


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware que captura o tenant_id do JWT ou do header X-Barbearia-Id
    e o injeta no contexto. Também configura o RLS no PostgreSQL.
    
    📖 MANIFESTO: "Um middleware captura o identificador do tenant"
    
    ✅ Regras seguidas:
    - Prioridade: Header X-Barbearia-Id > JWT tenant_id
    - Valida se o usuário tem acesso à barbearia selecionada
    - Injeta no ContextVar (thread-safe)
    - Configura RLS no PostgreSQL (defesa em profundidade)
    - Limpa contexto após requisição
    """
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Extrai tenant_id do header ou JWT e o injeta no contexto."""
        # Limpa contexto anterior (evita vazamento entre requisições)
        clear_context()
        
        # Se não há usuário autenticado, não há tenant
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        
        # CLIENTE_FINAL não precisa de contexto de tenant
        if tipo_usuario == 'CLIENTE_FINAL':
            return None
        
        # ═══════════════════════════════════════════════════════════
        # PRIORIDADE 1: Header X-Barbearia-Id (seletor de barbearia)
        # ═══════════════════════════════════════════════════════════
        barbearia_id_header = request.META.get('HTTP_X_BARBEARIA_ID')
        tenant_id: Optional[UUID] = None
        
        if barbearia_id_header:
            try:
                tenant_id = UUID(barbearia_id_header)
            except (ValueError, TypeError):
                return JsonResponse(
                    {
                        'success': False,
                        'error': 'Header X-Barbearia-Id inválido. Deve ser um UUID.'
                    },
                    status=400
                )
            
            # Validação de Segurança: O usuário tem acesso a esta barbearia?
            if not self._usuario_tem_acesso(request.user, tenant_id):
                return JsonResponse(
                    {
                        'success': False,
                        'error': 'Acesso negado. Você não tem vínculo com esta barbearia.',
                        'details': {'barbearia_id': str(tenant_id)}
                    },
                    status=403
                )
        
        # ═══════════════════════════════════════════════════════════
        # PRIORIDADE 2: tenant_id do JWT (fallback)
        # ═══════════════════════════════════════════════════════════
        if not tenant_id:
            tenant_id = getattr(request.user, 'tenant_id', None)
        
        # ═══════════════════════════════════════════════════════════
        # INJEÇÃO NO CONTEXTO (mantém compatibilidade com código existente)
        # ═══════════════════════════════════════════════════════════
        user_id = getattr(request.user, 'id', None)
        
        # Injeta no ContextVar (thread-safe)
        if tenant_id:
            request.barbearia_id = tenant_id
            set_current_tenant_id(tenant_id)
            logger.info(f"Middleware: tenant_id {tenant_id} (Header:{barbearia_id_header is not None})")
        
        if user_id:
            set_current_user_id(user_id)
            request.user_id = user_id  # Para compatibilidade com views
        
        # Defesa em profundidade: configura RLS no PostgreSQL
        if tenant_id:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SET LOCAL app.current_tenant = %s",
                        [str(tenant_id)]
                    )
            except (OperationalError, DatabaseError):
                logger.exception(
                    'Falha crítica ao setar contexto de tenant no PostgreSQL'
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
    
    def _usuario_tem_acesso(self, user, barbearia_id: UUID) -> bool:
        """
        Verifica se o usuário tem acesso à barbearia especificada.
        - DONO: criou a barbearia
        - BARBEIRO: tem vínculo ativo como Profissional
        """
        from apps.tenants.models import Barbearia
        from apps.operacional.models import Profissional
        
        tipo_usuario = getattr(user, 'tipo_usuario', None)
        
        if tipo_usuario == 'DONO':
            return Barbearia.objects.filter(
                id=barbearia_id,
                created_by=user,
                is_deleted=False
            ).exists()
        
        if tipo_usuario == 'BARBEIRO':
            return Profissional.objects.filter(
                usuario=user,
                barbearia_id=barbearia_id,
                ativo=True
            ).exists()
        
        return False


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