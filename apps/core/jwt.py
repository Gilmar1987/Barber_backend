# [Domínio: core] [Skill: jwt]

import logging
from typing import Optional
from uuid import UUID

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

logger = logging.getLogger(__name__)


def _resolve_tenant_id(user) -> Optional[str]:
    """Resolve o tenant_id do usuário."""
    from apps.tenants.models import Barbearia
    from apps.operacional.models import Profissional

    tipo = getattr(user, 'tipo_usuario', None)

    if tipo == 'DONO':
        barbearia = Barbearia.objects.filter(created_by=user, is_deleted=False).first()
        return str(barbearia.id) if barbearia else None

    if tipo == 'BARBEIRO':
        profissional = Profissional.objects.filter(usuario=user, ativo=True).first()
        return str(profissional.barbearia_id) if profissional else None

    return None


class BarberHubTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Injeta tenant_id e tipo_usuario no payload do JWT no momento do login."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['tenant_id'] = _resolve_tenant_id(user)
        token['tipo_usuario'] = getattr(user, 'tipo_usuario', None)
        return token


class BarberHubJWTAuthentication(JWTAuthentication):
    """
    Lê tenant_id e tipo_usuario do payload do JWT e popula o objeto request.user.
    """

    def get_user(self, validated_token):
        # 1. Obtém o usuário do banco de dados
        user = super().get_user(validated_token)
        
        # 2. LOG DE PROVA: Se este log não aparecer, o arquivo não foi salvo/carregado
        logger.info(f"🔍 DEBUG JWT - Token validado. tenant_id no token: {validated_token.get('tenant_id')}")
        
        # 3. Injeta o tenant_id
        raw_tenant = validated_token.get('tenant_id')
        if raw_tenant:
            try:
                user.tenant_id = UUID(raw_tenant)
                logger.info(f"✅ DEBUG JWT - user.tenant_id definido com sucesso: {user.tenant_id}")
            except (ValueError, AttributeError) as e:
                logger.error(f"❌ DEBUG JWT - Erro ao converter tenant_id: {e}")
                user.tenant_id = None
        else:
            logger.warning("⚠️ DEBUG JWT - Chave 'tenant_id' NÃO encontrada no token!")
            user.tenant_id = None
            
        # 4. Injeta o tipo_usuario (CRUCIAL para as Views funcionarem)
        user.tipo_usuario = validated_token.get('tipo_usuario')
        logger.info(f"🔍 DEBUG JWT - user.tipo_usuario definido como: '{user.tipo_usuario}'")
        
        return user


class BarberHubJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """Registra BarberHubJWTAuthentication no drf-spectacular."""
    target_class = 'apps.core.jwt.BarberHubJWTAuthentication'
    name = 'jwtAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }