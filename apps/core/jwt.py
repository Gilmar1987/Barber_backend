# [Domínio: core] [Skill: jwt]
from typing import Optional
from uuid import UUID

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def _resolve_tenant_id(user) -> Optional[str]:
    """
    Resolve o tenant_id do usuário:
    - DONO: barbearia onde é created_by
    - BARBEIRO: barbearia onde tem vínculo como Profissional ativo
    - CLIENTE_FINAL: None (acesso global ao marketplace)
    """
    from apps.tenants.models import Barbearia
    from apps.operacional.models import Profissional

    tipo = getattr(user, 'tipo_usuario', None)

    if tipo == 'DONO':
        barbearia = Barbearia.objects.filter(
            created_by=user, is_deleted=False
        ).first()
        return str(barbearia.id) if barbearia else None

    if tipo == 'BARBEIRO':
        profissional = Profissional.objects.filter(
            usuario=user, ativo=True
        ).first()
        return str(profissional.barbearia_id) if profissional else None

    return None


class BarberHubTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Injeta tenant_id no payload do JWT no momento do login."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        tenant_id = _resolve_tenant_id(user)
        token['tenant_id'] = tenant_id
        token['tipo_usuario'] = getattr(user, 'tipo_usuario', None)
        return token


class BarberHubJWTAuthentication(JWTAuthentication):
    """Lê tenant_id do payload do JWT e popula request.user.tenant_id."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        raw = validated_token.get('tenant_id')
        if raw:
            try:
                user.tenant_id = UUID(raw)
            except (ValueError, AttributeError):
                user.tenant_id = None
        else:
            user.tenant_id = None
        return user


class BarberHubJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """Registra BarberHubJWTAuthentication no drf-spectacular (restaura botão Authorize)."""
    target_class = 'apps.core.jwt.BarberHubJWTAuthentication'
    name = 'jwtAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
