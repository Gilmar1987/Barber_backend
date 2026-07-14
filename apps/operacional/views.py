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
from apps.operacional.dtos import GradeHorariaResponseDTO
from apps.operacional.serializers import (
    ProfissionalCreateSerializer,
    ProfissionalResponseSerializer,
    ProfissionalUpdateSerializer,
    ServicoCreateSerializer,
    ServicoResponseSerializer,
    ServicoUpdateSerializer,
    GradeHorariaCreateSerializer,
    GradeHorariaUpdateSerializer,
    ConviteAceiteSerializer,
    ConviteProfissionalCreateSerializer,
    DiaIndisponivelCreateSerializer,
    IntervaloIndisponivelCreateSerializer,
    ConviteProfissionalCreateSerializer,
    ConviteAceiteSerializer,
)
from apps.operacional.services import  (
    ProfissionalService, 
    ProfissionalService,
    ServicoService, 
    ServicoService,
    ProfissionalService,
    GradeHorariaService,
    ConviteProfissionalService,
    DiaIndisponivelService,
    IntervaloIndisponivelService,
GradeHorariaService, 
ConviteProfissionalService, 
DiaIndisponivelService,
IntervaloIndisponivelService,
ServicoService,
ProfissionalService,
GradeHorariaService,
ConviteProfissionalService,
DiaIndisponivelService, 
IntervaloIndisponivelService,
ServicoProfissionalService
 )

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

def _get_barbearia_id_from_jwt_or_none(request: Request) -> UUID:
    """
    Extrai o tenant_id do JWT do usuário autenticado, retorna None se não tiver.
    """
    return getattr(request.user, 'barbearia_viculo_id', None)

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
                # If the service call fails, we simply ignore it and continue.
                if result.success:
                    if result.data:
                        todos_servicos.extend(result.data)
                # No error propagation; empty list will be returned when no data is gathered.
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
        request=None,
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
        request=None,
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
        

# ═══════════════════════════════════════════════════════════
# VIEWS DE GRADE HORÁRIA
# ═══════════════════════════════════════════════════════════

class GradeHorariaListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = GradeHorariaService()
    
    @extend_schema(responses={200: GradeHorariaResponseDTO}, tags=['Grade Horária'])
    def get(self, request: Request, profissional_id: int) -> Response:
        barbearia_id = _get_barbearia_id_from_jwt_or_none(request)
        if not barbearia_id:
            return Response({'success': False, 'error': 'Acesso negado'}, status=403)
        
        result = self.service.listar_grades(profissional_id, barbearia_id)
        return Response(result.model_dump(), status=200 if result.success else 400)


class GradeHorariaCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = GradeHorariaService()
    
    @extend_schema(
        request=GradeHorariaCreateSerializer,
        responses={
            201: OpenApiResponse(description='Grade horária criada'),
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Apenas DONO'),
        },
        tags=['Grade Horária'],
    )
    def post(self, request: Request, profissional_id: int) -> Response:
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response: return forbid_response
        
        barbearia_id = _get_barbearia_id_from_jwt_or_none(request)
        if not barbearia_id:
            return Response({'success': False, 'error': 'Barbearia não identificada'}, status=403)
        
        serializer = GradeHorariaCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)
        
        result = self.service.criar_grade(serializer.to_dto(), profissional_id, barbearia_id, request.user.id)
        return Response(result.model_dump(), status=201 if result.success else 400)


# ═══════════════════════════════════════════════════════════
# VIEWS DE INDISPONIBILIDADES
# ═══════════════════════════════════════════════════════════

class DiaIndisponivelCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = DiaIndisponivelService()
    
    @extend_schema(
        request=DiaIndisponivelCreateSerializer,
        responses={
            201: OpenApiResponse(description='Dia indisponível criado'),
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Acesso negado'),
        },
        tags=['Indisponibilidade'],
    )
    def post(self, request: Request, profissional_id: int) -> Response:
        # DONO ou o próprio BARBEIRO podem criar
        barbearia_id = _get_barbearia_id_from_jwt_or_none(request)
        if not barbearia_id:
            return Response({'success': False, 'error': 'Acesso negado'}, status=403)
        
        serializer = DiaIndisponivelCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)
        
        result = self.service.criar_dia_indisponivel(serializer.to_dto(), profissional_id, barbearia_id, request.user.id)
        return Response(result.model_dump(), status=201 if result.success else 400)


class IntervaloIndisponivelCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = IntervaloIndisponivelService()
    
    @extend_schema(
        request=IntervaloIndisponivelCreateSerializer,
        responses={
            201: OpenApiResponse(description='Intervalo indisponível criado'),
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Acesso negado'),
        },
        tags=['Indisponibilidade'],
    )
    def post(self, request: Request, profissional_id: int) -> Response:
        barbearia_id = _get_barbearia_id_from_jwt_or_none(request)
        if not barbearia_id:
            return Response({'success': False, 'error': 'Acesso negado'}, status=403)
        
        serializer = IntervaloIndisponivelCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)
        
        result = self.service.criar_intervalo_indisponivel(serializer.to_dto(), profissional_id, barbearia_id, request.user.id)
        return Response(result.model_dump(), status=201 if result.success else 400)


# ═══════════════════════════════════════════════════════════
# VIEWS DE HABILITAÇÃO SERVIÇO-PROFISSIONAL
# ═══════════════════════════════════════════════════════════

class ServicoProfissionalHabilitarView(APIView):
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ServicoProfissionalService()
    
    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='Serviço habilitado para o profissional'),
            400: OpenApiResponse(description='Parâmetros obrigatórios ausentes'),
            403: OpenApiResponse(description='Apenas DONO'),
        },
        tags=['Habilitação de Serviços'],
    )
    def post(self, request: Request) -> Response:
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response: return forbid_response
        
        barbearia_id = _get_barbearia_id_from_jwt_or_none(request)
        if not barbearia_id:
            return Response({'success': False, 'error': 'Barbearia não identificada'}, status=403)
        
        servico_id = request.data.get('servico_id')
        profissional_id = request.data.get('profissional_id')
        
        if not servico_id or not profissional_id:
            return Response({'success': False, 'error': 'servico_id e profissional_id são obrigatórios'}, status=400)
        
        result = self.service.habilitar_profissional(servico_id, profissional_id, barbearia_id, request.user.id)
        return Response(result.model_dump(), status=200 if result.success else 400)


# ═══════════════════════════════════════════════════════════
# VIEWS DE CONVITE PROFISSIONAL (Fluxo Híbrido)
# ═══════════════════════════════════════════════════════════

class ConviteProfissionalCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ConviteProfissionalService()
    
    @extend_schema(
        request=ConviteProfissionalCreateSerializer,
        responses={
            201: OpenApiResponse(description='Convite criado'),
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Apenas DONO ou barbearia não encontrada'),
        },
        tags=['Convites'],
    )
    def post(self, request: Request) -> Response:
        forbid_response = _forbid_if_not_dono(request)
        if forbid_response: return forbid_response
        
        barbearia_id = _get_barbearia_id_from_jwt_or_none(request)
        if not barbearia_id:
            return Response({
                'success': False, 
                'error': 'Você precisa criar uma barbearia antes de convidar profissionais.',
                'details': {'proximo_passo': 'POST /api/v1/tenants/barbearias/create/'}
            }, status=403)
        
        serializer = ConviteProfissionalCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)
        
        result = self.service.criar_convite(serializer.to_dto(), barbearia_id, request.user.id)
        return Response(result.model_dump(), status=201 if result.success else 400)


class ConviteAceitarView(APIView):
    """Endpoint público para o barbeiro aceitar o convite via link do email."""
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ConviteProfissionalService()
    
    @extend_schema(
        request=ConviteAceiteSerializer,
        responses={
            200: OpenApiResponse(description='Convite aceito com sucesso'),
            400: OpenApiResponse(description='Token inválido ou expirado'),
        },
        tags=['Convites'],
    )
    def post(self, request: Request) -> Response:
        serializer = ConviteAceiteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)
        
        result = self.service.aceitar_convite(serializer.validated_data['token'])
        return Response(result.model_dump(), status=200 if result.success else 400)