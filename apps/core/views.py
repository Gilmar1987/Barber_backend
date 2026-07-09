# [Domínio: core] [Skill: view]
"""
📖 MANIFESTO (Skill 04 - View):
"Captura a identificação do usuário autenticado no JWT para fins de auditoria"

✅ Regras seguidas:
- Views são finas (delegam lógica para Services)
- Views extraem user_id do JWT para auditoria
- Views convertem Serializer → Pydantic DTO
- Views não acessam Models diretamente
"""
import logging
from uuid import UUID

from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import (
    UsuarioCreateSerializer,
    UsuarioResponseSerializer,
    UsuarioUpdateSerializer,
)
from apps.core.service import UsuarioService

logger = logging.getLogger(__name__)


class UsuarioCreateView(APIView):
    """POST /api/v1/core/usuarios/create/"""
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = UsuarioService()
    
    @extend_schema(
        request=UsuarioCreateSerializer,
        responses={201: UsuarioResponseSerializer},
        tags=['Usuários'],
    )
    def post(self, request: Request) -> Response:
        serializer = UsuarioCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dto = serializer.to_dto()
        result = self.service.criar_usuario(dto)

        if result.success:
            return Response(result.model_dump(), status=status.HTTP_201_CREATED)
        return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)


class UsuarioDetailView(APIView):
    """GET / PUT / DELETE /api/v1/core/usuarios/{user_id}/"""
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = UsuarioService()
    
    @extend_schema(
        responses={200: UsuarioResponseSerializer},
        tags=['Usuários'],
    )
    def get(self, request: Request, user_id: UUID) -> Response:
        result = self.service.obter_usuario(user_id)
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        request=UsuarioUpdateSerializer,
        responses={200: UsuarioResponseSerializer},
        tags=['Usuários'],
    )
    def put(self, request: Request, user_id: UUID) -> Response:
        if request.user.id != user_id and not request.user.is_staff:
            return Response(
                {'success': False, 'error': 'Sem permissão.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UsuarioUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dto = serializer.to_dto()
        updated_by = request.user.id
        result = self.service.atualizar_usuario(user_id, dto, updated_by=updated_by)
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        responses={200: OpenApiResponse(description='Usuário deletado')},
        tags=['Usuários'],
    )
    def delete(self, request: Request, user_id: UUID) -> Response:
        if request.user.id != user_id and not request.user.is_staff:
            return Response(
                {'success': False, 'error': 'Sem permissão.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deleted_by = request.user.id
        result = self.service.deletar_usuario(user_id, deleted_by=deleted_by)
        
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        if result.details and result.details.get('user_id'):
            return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)
        return Response(result.model_dump(), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UsuarioListView(APIView):
    """GET /api/v1/core/usuarios/"""
    permission_classes = [IsAdminUser]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = UsuarioService()
    
    @extend_schema(
        responses={200: UsuarioResponseSerializer(many=True)},
        tags=['Usuários'],
    )
    def get(self, request: Request) -> Response:
        tipo_usuario = request.query_params.get('tipo_usuario')
        result = self.service.listar_usuarios(tipo_usuario)
        return Response(result.model_dump(), status=status.HTTP_200_OK)


class UsuarioMeView(APIView):
    """GET /api/v1/core/usuarios/me/"""
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = UsuarioService()
    
    @extend_schema(
        responses={200: UsuarioResponseSerializer},
        tags=['Usuários'],
    )
    def get(self, request: Request) -> Response:
        result = self.service.obter_usuario(request.user.id)
        if result.success:
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        return Response(result.model_dump(), status=status.HTTP_404_NOT_FOUND)