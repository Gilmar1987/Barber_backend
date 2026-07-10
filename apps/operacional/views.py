# [Domínio: operacional] [Skill: view]
"""
📖 MANIFESTO (Skill 04 - View):
"Views são finas — toda lógica reside no Service"
"Captura a identificação do usuário autenticado no JWT para fins de auditoria"

📖 MANIFESTO (Negative Constraints):
"PROIBIDO acessar Models ou Repositories diretamente nas Views"
"PROIBIDO realizar consultas diretas ao banco nas Views"

 MANIFESTO (Multi-tenancy - US06):
"barbearia_id é extraído do JWT (barbearia_vinculo_id), nunca do request"
"Middleware confronta ID do JWT com parâmetro da URL e retorna 403 se divergir"

📖 MANIFESTO (Permissões):
"CLIENTE_FINAL: vê apenas ativos de todas as barbearias (marketplace global)"
"BARBEIRO: vê todos (ativos/inativos) apenas da sua barbearia"
"DONO: vê todos (ativos/inativos) apenas da sua barbearia, pode criar/editar"

✅ Regras seguidas:
- Views são finas (delegam lógica para Services)
- Views extraem barbearia_id do JWT para isolamento multi-tenant
- Views convertem Serializer → Pydantic DTO
- Views NÃO acessam Models/Repositories diretamente
- Documentação automática via @extend_schema (drf-spectacular)
- Permissões claras por perfil (CLIENTE_FINAL, BARBEIRO, DONO)
- HTTP status codes corretos (201, 200, 400, 403, 404, 500)
"""
import logging
from uuid import UUID

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.operacional.serializers import (
    ProfissionalCreateSerializer,
    ProfissionalResponseSerializer,
    ProfissionalUpdateSerializer,
    ServicoCreateSerializer,
    ServicoResponseSerializer,
    ServicoUpdateSerializer,
)
from apps.operacional.services import ProfissionalService, ServicoService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# HELPERS: Extração segura de barbearia_id do JWT
# ═══════════════════════════════════════════════════════════

def _get_barbearia_id_from_jwt(request: Request) -> UUID:
    """
    Extrai o tenant_id do JWT do usuário autenticado (barbearia vinculada).
    Lança exceção se o usuário não tiver vínculo com barbearia.
    """
    barbearia_id = getattr(request.user, 'tenant_id', None)
    if not barbearia_id:
        raise ValueError(
            "Usuário não possui vínculo com barbearia. "
            "Apenas DONO e BARBEIRO podem acessar esta operação."
        )
    return barbearia_id


def _forbid_if_not_dono(request: Request) -> Response:
    """
    Retorna 403 se o usuário não for DONO.
    Deve ser chamado antes de operações de escrita.
    """
    if getattr(request.user, 'tipo_usuario', None) != 'DONO':
        return Response(
            {
                'success': False,
                'error': 'Acesso negado. Apenas DONO pode executar esta operação.',
                'details': {
                    'tipo_usuario_atual': getattr(request.user, 'tipo_usuario', 'desconhecido'),
                    'tipo_usuario_necessario': 'DONO'
                }
            },
            status=status.HTTP_403_FORBIDDEN
        )
    return None


# ═══════════════════════════════════════════════════════════
# VIEWS DE SERVIÇO
# ═══════════════════════════════════════════════════════════

class ServicoListView(APIView):
    """
    GET /api/v1/operacional/servicos/
    Lista serviços conforme o perfil do usuário:
    - CLIENTE_FINAL: ativos de todas as barbearias (marketplace)
    - BARBEIRO/DONO: todos (ativos/inativos) da sua barbearia
    """
    permission_classes = [AllowAny]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ServicoService()
    
    @extend_schema(
        responses={200: ServicoResponseSerializer(many=True)},
        tags=['Serviços'],
    )
    def get(self, request: Request) -> Response:
        """Lista serviços conforme permissão do perfil."""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        
        # CLIENTE_FINAL não autenticado ou autenticado: vê ativos de todas
        if tipo_usuario == 'CLIENTE_FINAL' or not request.user.is_authenticated:
            from apps.tenants.repository import BarbeariaRepository
            barbearias_ativas = BarbeariaRepository.get_all_active()
            todos_servicos = []
            for barbearia in barbearias_ativas:
                result = self.service.listar_servicos(barbearia.id, ativo_only=True)
                if result.success and result.data:
                    todos_servicos.extend(result.data)
            return Response({
                'success': True,
                'data': [s.model_dump() for s in todos_servicos],
                'error': None,
                'details': None
            }, status=status.HTTP_200_OK)
        
        # BARBEIRO ou DONO: vê da sua barbearia (ativos e inativos)
        if tipo_usuario in ('BARBEIRO', 'DONO'):
            try:
                barbearia_id = _get_barbearia_id_from_jwt(request)
            except ValueError as e:
                return Response(
                    {'success': False, 'error': str(e)},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # DONO e BARBEIRO veem todos (ativos e inativos) da sua barbearia
            result = self.service.listar_servicos(barbearia_id, ativo_only=False)
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        
        return Response(
            {'success': False, 'error': 'Perfil de usuário não reconhecido'},
            status=status.HTTP_403_FORBIDDEN
        )


class ServicoDetailView(APIView):
    """
    GET /api/v1/operacional/servicos/{servico_id}/
    Retorna detalhes de um serviço específico.
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ServicoService()
    
    @extend_schema(
        responses={
            200: ServicoResponseSerializer,
            403: OpenApiResponse(description='Acesso negado'),
            404: OpenApiResponse(description='Serviço não encontrado'),
        },
        tags=['Serviços'],
    )
    def get(self, request: Request, servico_id: int) -> Response:
        """Retorna detalhes de um serviço."""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        
        # CLIENTE_FINAL: pode ver qualquer serviço ativo (marketplace)
        if tipo_usuario == 'CLIENTE_FINAL':
            from apps.tenants.repository import BarbeariaRepository
            for barbearia in BarbeariaRepository.get_all_active():
                result = self.service.obter_servico(servico_id, barbearia.id)
                if result.success:
                    return Response(result.model_dump(), status=status.HTTP_200_OK)
            return Response(
                {'success': False, 'error': 'Serviço não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # BARBEIRO ou DONO: só pode ver serviços da sua barbearia
        if tipo_usuario in ('BARBEIRO', 'DONO'):
            try:
                barbearia_id = _get_barbearia_id_from_jwt(request)
            except ValueError as e:
                return Response(
                    {'success': False, 'error': str(e)},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            result = self.service.obter_servico(servico_id, barbearia_id)
            if result.success:
                return Response(result.model_dump(), status=status.HTTP_200_OK)
            else:
                return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
        
        return Response(
            {'success': False, 'error': 'Perfil não reconhecido'},
            status=status.HTTP_403_FORBIDDEN
        )


class ServicoCreateView(APIView):
    """
    POST /api/v1/operacional/servicos/create/
    Cria novo serviço (apenas DONO).
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ServicoService()
    
    @extend_schema(
        request=ServicoCreateSerializer,
        responses={
            201: ServicoResponseSerializer,
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Apenas DONO pode criar serviços'),
        },
        tags=['Serviços'],
    )
    def post(self, request: Request) -> Response:
        """Cria novo serviço (apenas DONO)."""
        # Validação de permissão: apenas DONO
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response:
            return forbid_response
        
        # Extrai barbearia_id do JWT
        try:
            barbearia_id = _get_barbearia_id_from_jwt(request)
        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validação do payload
        serializer = ServicoCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Converte para Pydantic DTO
        dto = serializer.to_dto()
        
        # Delega para o Service
        result = self.service.criar_servico(
            dto, barbearia_id, user_id=request.user.id
        )
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_201_CREATED)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)


class ServicoUpdateView(APIView):
    """
    PUT /api/v1/operacional/servicos/{servico_id}/
    Atualiza serviço existente (apenas DONO).
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ServicoService()
    
    @extend_schema(
        request=ServicoUpdateSerializer,
        responses={
            200: ServicoResponseSerializer,
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Apenas DONO pode atualizar'),
            404: OpenApiResponse(description='Serviço não encontrado'),
        },
        tags=['Serviços'],
    )
    def put(self, request: Request, servico_id: int) -> Response:
        """Atualiza serviço (apenas DONO)."""
        # Validação de permissão: apenas DONO
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response:
            return forbid_response
        
        # Extrai barbearia_id do JWT
        try:
            barbearia_id = _get_barbearia_id_from_jwt(request)
        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validação do payload
        serializer = ServicoUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dto = serializer.to_dto()
        
        result = self.service.atualizar_servico(
            servico_id, barbearia_id, dto, updated_by=request.user.id
        )
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        elif 'não encontrado' in (result.error or '').lower():
            return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)


class ServicoToggleAtivoView(APIView):
    """
    POST /api/v1/operacional/servicos/{servico_id}/toggle/
    Alterna status ativo/inativo do serviço (apenas DONO).
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ServicoService()
    
    @extend_schema(
        responses={
            200: ServicoResponseSerializer,
            403: OpenApiResponse(description='Apenas DONO'),
            404: OpenApiResponse(description='Serviço não encontrado'),
        },
        tags=['Serviços'],
    )
    def post(self, request: Request, servico_id: int) -> Response:
        """Toggle ativo/inativo (apenas DONO)."""
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response:
            return forbid_response
        
        try:
            barbearia_id = _get_barbearia_id_from_jwt(request)
        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        result = self.service.toggle_ativo_servico(
            servico_id, barbearia_id, user_id=request.user.id
        )
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        elif 'não encontrado' in (result.error or '').lower():
            return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════
# VIEWS DE PROFISSIONAL
# ═══════════════════════════════════════════════════════════

class ProfissionalListView(APIView):
    """
    GET /api/v1/operacional/profissionais/
    Lista profissionais conforme o perfil do usuário.
    """
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ProfissionalService()
    
    @extend_schema(
        responses={200: ProfissionalResponseSerializer(many=True)},
        tags=['Profissionais'],
    )
    def get(self, request: Request) -> Response:
        """Lista profissionais conforme permissão do perfil."""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        
        # CLIENTE_FINAL: vê ativos de todas as barbearias (marketplace)
        if tipo_usuario == 'CLIENTE_FINAL' or not request.user.is_authenticated:
            from apps.tenants.repository import BarbeariaRepository
            barbearias_ativas = BarbeariaRepository.get_all_active()
            todos_profissionais = []
            for barbearia in barbearias_ativas:
                result = self.service.listar_profissionais(barbearia.id, ativo_only=True)
                if result.success and result.data:
                    todos_profissionais.extend(result.data)
            return Response({
                'success': True,
                'data': [p.model_dump() for p in todos_profissionais],
                'error': None,
                'details': None
            }, status=status.HTTP_200_OK)
        
        # BARBEIRO ou DONO: vê da sua barbearia
        if tipo_usuario in ('BARBEIRO', 'DONO'):
            try:
                barbearia_id = _get_barbearia_id_from_jwt(request)
            except ValueError as e:
                return Response(
                    {'success': False, 'error': str(e)},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            result = self.service.listar_profissionais(barbearia_id, ativo_only=False)
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        
        return Response(
            {'success': False, 'error': 'Perfil não reconhecido'},
            status=status.HTTP_403_FORBIDDEN
        )


class ProfissionalCreateView(APIView):
    """
    POST /api/v1/operacional/profissionais/create/
    Cadastra novo profissional (apenas DONO).
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ProfissionalService()
    
    @extend_schema(
        request=ProfissionalCreateSerializer,
        responses={
            201: ProfissionalResponseSerializer,
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Apenas DONO'),
        },
        tags=['Profissionais'],
    )
    def post(self, request: Request) -> Response:
        """Cadastra novo profissional (apenas DONO)."""
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response:
            return forbid_response
        
        try:
            barbearia_id = _get_barbearia_id_from_jwt(request)
        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProfissionalCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dto = serializer.to_dto()
        
        result = self.service.criar_profissional(
            dto, barbearia_id, user_id=request.user.id
        )
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_201_CREATED)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)


class ProfissionalUpdateView(APIView):
    """
    PUT /api/v1/operacional/profissionais/{profissional_id}/
    Atualiza profissional (apenas DONO).
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ProfissionalService()
    
    @extend_schema(
        request=ProfissionalUpdateSerializer,
        responses={
            200: ProfissionalResponseSerializer,
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Apenas DONO'),
            404: OpenApiResponse(description='Profissional não encontrado'),
        },
        tags=['Profissionais'],
    )
    def put(self, request: Request, profissional_id: int) -> Response:
        """Atualiza profissional (apenas DONO)."""
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response:
            return forbid_response
        
        try:
            barbearia_id = _get_barbearia_id_from_jwt(request)
        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProfissionalUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dto = serializer.to_dto()
        
        result = self.service.atualizar_profissional(
            profissional_id, barbearia_id, dto, updated_by=request.user.id
        )
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        elif 'não encontrado' in (result.error or '').lower():
            return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)


class ProfissionalToggleAtivoView(APIView):
    """
    POST /api/v1/operacional/profissionais/{profissional_id}/toggle/
    Alterna status ativo/inativo (apenas DONO).
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ProfissionalService()
    
    @extend_schema(
        responses={
            200: ProfissionalResponseSerializer,
            403: OpenApiResponse(description='Apenas DONO'),
            404: OpenApiResponse(description='Profissional não encontrado'),
        },
        tags=['Profissionais'],
    )
    def post(self, request: Request, profissional_id: int) -> Response:
        """Toggle ativo/inativo (apenas DONO)."""
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response:
            return forbid_response
        
        try:
            barbearia_id = _get_barbearia_id_from_jwt(request)
        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        result = self.service.toggle_ativo_profissional(
            profissional_id, barbearia_id, user_id=request.user.id
        )
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        elif 'não encontrado' in (result.error or '').lower():
            return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)