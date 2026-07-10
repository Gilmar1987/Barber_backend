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

from drf_spectacular.utils import extend_schema, OpenApiResponse
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
        },
        description='Cria uma nova barbearia (tenant) no sistema.',
        tags=['Barbearias'],
    )
    def post(self, request: Request) -> Response:
        """Cria nova barbearia."""
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
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BarbeariaService()
    
    @extend_schema(
        responses={
            200: BarbeariaResponseSerializer,
            404: OpenApiResponse(description='Barbearia não encontrada'),
        },
        tags=['Barbearias'],
    )
    def get(self, request: Request, barbearia_id: UUID) -> Response:
        """Retorna dados de uma barbearia específica."""
        result = self.service.obter_barbearia(barbearia_id)
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        else:
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
        """Lista todas as barbearias ativas."""
        result = self.service.listar_barbearias()
        return Response(result.model_dump(), status=status.HTTP_200_OK)


class BarbeariaProximidadeView(APIView):
    """
    GET /api/v1/tenants/barbearias/proximidade/
    Busca barbearias por proximidade geográfica.
    """
    permission_classes = [AllowAny]  # Público para busca
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BarbeariaService()
    
    @extend_schema(
        parameters=[ProximidadeSearchSerializer],
        responses={200: BarbeariaListWithDistanceSerializer(many=True)},
        description='Busca barbearias por proximidade geográfica (raio em km).',
        tags=['Barbearias'],
    )
    def get(self, request: Request) -> Response:
        """Busca barbearias por proximidade."""
        serializer = ProximidadeSearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Converte para Pydantic DTO
        search_dto = serializer.to_dto()
        
        # Delega para o Service
        result = self.service.buscar_por_proximidade(search_dto)
        
        return Response(result.model_dump(), status=status.HTTP_200_OK)
