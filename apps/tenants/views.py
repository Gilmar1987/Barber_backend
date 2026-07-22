# [Domínio: tenants] [Skill: view]
"""
📖 MANIFESTO (Skill 04 - View):
"Captura a identificação do usuário autenticado no JWT para fins de auditoria"
"Views são finas — toda lógica reside no Service"

📖 MANIFESTO (Negative Constraints):
"PROIBIDO acessar Models ou Repositories diretamente nas Views"
"PROIBIDO realizar consultas diretas ao banco nas Views"

✅ Regras seguidas:
- Views são finas (delegam lógica para Services)
- Views extraem user_id do JWT para auditoria
- Views convertem Serializer → Pydantic DTO
- Views NÃO acessam Models/Repositories diretamente
- Documentação automática via @extend_schema (drf-spectacular)
- Permissões claras (AllowAny, IsAuthenticated, IsAdminUser)
- HTTP status codes corretos (201, 200, 400, 404, 500)
"""
import logging
from uuid import UUID
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, OpenApiTypes
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.serializers import (
    BarbeariaCreateSerializer,
    BarbeariaListSerializer,
    BarbeariaListWithDistanceSerializer,
    BarbeariaResponseSerializer,
    BarbeariaUpdateSerializer,
    ProximidadeSearchSerializer,
)
from apps.tenants.services import BarbeariaService
from apps.core.models import VinculoUsuarioBarbearia

logger = logging.getLogger(__name__)


class BarbeariaCreateView(APIView):
    """
    POST /api/v1/tenants/barbearias/create/
    Cria nova barbearia (público — qualquer usuário autenticado).
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BarbeariaService()
    
    @extend_schema(
        request=BarbeariaCreateSerializer,
        responses={
            201: BarbeariaResponseSerializer,
            400: OpenApiResponse(description='Erro de validação'),
            403: OpenApiResponse(description='Acesso negado, apenas usuário DONO pode criar barbearia '),
            409: OpenApiResponse(description='Barbearia com CNPJ ou email já existe')
        },
        description='Cria uma nova barbearia (tenant) no sistema.',
        tags=['Barbearias'],
    )
    def post(self, request: Request) -> Response:
        """Cria nova barbearia (apenas DONO pode criar)"""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        if tipo_usuario != 'DONO':
            return Response(
                {
                    'success': False, 
                    'error': 'Acesso negado. Apenas DONO pode criar barbearia.',
                    'details': {
                        'tipo_user': request.user.tipo_usuario,
                        'user_id': request.user.id,
                        'tipo_usuario_necessario': 'DONO'
                    }
                },
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = BarbeariaCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Converte para Pydantic DTO
        dto = serializer.to_dto()
        
        # Extrai user_id do JWT para auditoria
        user_id = request.user.id if request.user.is_authenticated else None
        
        # Delega para o Service
        result = self.service.criar_barbearia(dto, user_id=user_id)
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_201_CREATED)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)


class BarbeariaDetailView(APIView):
    """
    GET / PUT / DELETE /api/v1/tenants/barbearias/{barbearia_id}/
    """
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BarbeariaService()
    
    @extend_schema(
        responses={
            200: BarbeariaResponseSerializer,
            403: OpenApiResponse(description='Acesso negado apenas Dono pode realzar modificações'),
            404: OpenApiResponse(description='Barbearia não encontrada'),
        },
        tags=['Barbearias'],
    )
    def get(self, request: Request, barbearia_id: UUID) -> Response:
        """Retorna dados de uma barbearia específica."""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)

        # DONO e BARBEIRO só podem ver a própria barbearia
        if tipo_usuario in ('DONO', 'BARBEIRO'):
            tenant_id = getattr(request.user, 'tenant_id', None)
            if not tenant_id or tenant_id != barbearia_id:
                return Response(
                    {'success': False, 'error': 'Acesso negado. Você não tem permissão para acessar esta barbearia.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # CLIENTE_FINAL (autenticado ou não): pode ver qualquer barbearia ativa
        result = self.service.obter_barbearia(barbearia_id)
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        request=BarbeariaUpdateSerializer,
        responses={
            200: BarbeariaResponseSerializer,
            400: OpenApiResponse(description='Erro de validação'),
            404: OpenApiResponse(description='Barbearia não encontrada'),
        },
        tags=['Barbearias'],
    )
    def put(self, request: Request, barbearia_id: UUID) -> Response:
        """Atualiza barbearia existente."""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        tenant_id = getattr(request.user, 'tenant_id', None)

        if tipo_usuario != 'DONO' or not tenant_id or tenant_id != barbearia_id:
            return Response(
                {'success': False, 'error': 'Acesso negado. Apenas o DONO desta barbearia pode atualizá-la.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = BarbeariaUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Converte para Pydantic DTO
        dto = serializer.to_dto()
        
        # Extrai user_id do JWT para auditoria
        updated_by = request.user.id if request.user.is_authenticated else None
        
        # Delega para o Service
        result = self.service.atualizar_barbearia(
            barbearia_id, dto, updated_by=updated_by
        )
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        elif 'não encontrada' in (result.error or '').lower():
            return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description='Barbearia deletada'),
            404: OpenApiResponse(description='Barbearia não encontrada'),
        },
        tags=['Barbearias'],
    )
    def delete(self, request: Request, barbearia_id: UUID) -> Response:
        """Realiza soft delete da barbearia."""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        tenant_id = getattr(request.user, 'tenant_id', None)

        if tipo_usuario != 'DONO' or not tenant_id or tenant_id != barbearia_id:
            return Response(
                {'success': False, 'error': 'Acesso negado. Apenas o DONO desta barbearia pode excluí-la.'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Extrai user_id do JWT para auditoria
        deleted_by = request.user.id if request.user.is_authenticated else None
        
        # Delega para o Service
        result = self.service.deletar_barbearia(
            barbearia_id, deleted_by=deleted_by
        )
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        elif 'não encontrada' in (result.error or '').lower():
            return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(result.model_dump(), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BarbeariaListView(APIView):
    """
    GET /api/v1/tenants/barbearias/
    Lista todas as barbearias ativas.
    """
    permission_classes = [AllowAny]  # Público para busca
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BarbeariaService()
    
    @extend_schema(
        responses={200: BarbeariaListSerializer(many=True)},
        tags=['Barbearias'],
    )
    def get(self, request: Request) -> Response:
        """Lista barbearias conforme perfil do usuário."""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)

        # DONO e BARBEIRO: listam TODAS as barbearias que eles criam/possuem vínculo
        if tipo_usuario in ('DONO', 'BARBEIRO'):
            user_id = request.user.id if request.user.is_authenticated else None
            
            # O service agora filtra por created_by=user_id
            result = self.service.listar_barbearias(user_id=user_id)
            return Response(result.model_dump(), status=status.HTTP_200_OK)

        # CLIENTE_FINAL ou não autenticado: marketplace global (todas as ativas)
        result = self.service.listar_barbearias(user_id=None)
        return Response(result.model_dump(), status=status.HTTP_200_OK)
    
# apps/tenants/views.py

# apps/tenants/views.py


class BarbeariaProximidadeView(APIView):
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BarbeariaService()
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='latitude', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name='longitude', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name='raio_km', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, required=False, default=5),
        ],
        responses={200: BarbeariaListWithDistanceSerializer(many=True)},
        description='Busca barbearias por proximidade geográfica (raio em km).',
        tags=['Barbearias'],
    )
    def get(self, request: Request) -> Response:
        serializer = ProximidadeSearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        search_dto = serializer.to_dto()
        result = self.service.buscar_por_proximidade(search_dto)
        
        # ✅ CORREÇÃO CRÍTICA: result é um objeto Pydantic, use .success, não ['success']
        if not result.success:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)

        # ✅ Regra 10: Paginação Obrigatória
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginator.page_size_query_param = 'page_size'
        paginator.max_page_size = 100
        
        # Converter DTOs Pydantic para dicionários para o paginator do DRF
        data_dicts = [item.model_dump() for item in result.data]
        page = paginator.paginate_queryset(data_dicts, request)
        
        if page is not None:
            return Response({
                'success': True,
                'data': page,
                'error': None,
                'details': {
                    'count': paginator.page.paginator.count,
                    'next': paginator.get_next_link(),
                    'previous': paginator.get_previous_link(),
                    'page': paginator.page.number,
                    'page_size': paginator.page_size
                }
            }, status=status.HTTP_200_OK)
        
        # Fallback sem paginação (caso o paginator retorne None)
        return Response({
            'success': True,
            'data': data_dicts,
            'error': None,
            'details': None
        }, status=status.HTTP_200_OK)
    



# apps/tenants/views.py (ADICIONE AO FINAL DO ARQUIVO)

class BarbeariaContextoListView(APIView):
    """
    GET /api/v1/tenants/barbearias/meu-contexto/
    
    Lista todas as barbearias às quais o usuário autenticado tem vínculo.
    Usado pelo frontend para popular o seletor de barbearia (dropdown).
    
    📖 MANIFESTO (Skill 04 - View):
    - View fina: delega toda lógica ao Service
    - Extrai user_id do JWT (nunca do request.data)
    - Não acessa Models/Repositories diretamente
    
    📖 MANIFESTO (Multi-tenancy - US06):
    - Endpoint especial: NÃO exige barbearia_id no contexto
    - É justamente o endpoint que lista os contextos disponíveis
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BarbeariaService()
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description='Lista de contextos disponíveis'),
            401: OpenApiResponse(description='Não autenticado'),
            403: OpenApiResponse(description='Perfil não requer contexto (CLIENTE_FINAL)'),
        },
        description='Lista todas as barbearias às quais o usuário tem vínculo ativo.',
        tags=['Barbearias'],
    )
    def get(self, request: Request) -> Response:
        """Lista barbearias do usuário para o seletor de contexto."""
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        
        # CLIENTE_FINAL não precisa de contexto de barbearia
        if tipo_usuario == 'CLIENTE_FINAL':
            return Response(
                {
                    'success': False,
                    'error': 'Perfil CLIENTE_FINAL não requer contexto de barbearia.',
                    'details': {'tipo_usuario': tipo_usuario}
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Extrai user_id do JWT (Regra do Manifesto)
        user_id = request.user.id
        
        # Delega para o Service
        result = self.service.listar_contextos_usuario(user_id=user_id)
        
        if result.success:
            return Response(
                {
                    'success': True,
                    'data': [item.model_dump() for item in result.data],
                    'error': None,
                    'details': {'total': len(result.data)}
                },
                status=status.HTTP_200_OK
            )
        
        return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)