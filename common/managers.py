# [Domínio: core] [Skill: manager]
"""
📖 MANIFESTO (Skill 01 - Model):
"Os modelos herdam de um TenantBaseModel cujo manager customizado
(TenantManager) estende um TenantQuerySet que injeta automaticamente
o filtro WHERE tenant_id = X em todas as operações nativas do ORM."

📖 MANIFESTO (Negative Constraints):
"PROIBIDO realizar consultas diretas ao banco utilizando managers padrões
(ex: .objects.all()) em Service ou Views."

✅ Regras seguidas:
- TenantQuerySet injeta filtro de tenant automaticamente
- TenantManager usa TenantQuerySet como padrão
- unscoped_objects permite escape explícito para manutenção global
- Se não houver tenant no contexto, retorna queryset vazio (segurança)
"""
from typing import Optional
from uuid import UUID

from django.db import models

from common.context import get_current_tenant_id


class TenantQuerySet(models.QuerySet):
    """
    QuerySet que filtra automaticamente pelo tenant_id do contexto atual.
    """
    
    def for_tenant(self, tenant_id: Optional[UUID] = None) -> 'TenantQuerySet':
        """Filtra pelo tenant_id fornecido ou pelo contexto atual."""
        resolved_tenant = tenant_id or get_current_tenant_id()
        if not resolved_tenant:
            # Segurança: se não há tenant, retorna vazio (evita vazamento)
            return self.none()
        return self.filter(tenant_id=resolved_tenant)
    
    def all_for_tenant(self) -> 'TenantQuerySet':
        """Alias explícito para filtrar pelo tenant do contexto."""
        return self.for_tenant()


class TenantManager(models.Manager):
    """
    Manager que aplica automaticamente o filtro de tenant em todas as queries.
    """
    
    def get_queryset(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db).for_tenant()
    
    def for_tenant(self, tenant_id: Optional[UUID] = None) -> TenantQuerySet:
        """Permite filtrar por tenant específico (útil em testes)."""
        return TenantQuerySet(self.model, using=self._db).for_tenant(tenant_id)


class UnscopedManager(models.Manager):
    """
    Manager sem filtro de tenant (escape explícito para manutenção global).
    USO RESTRITO: apenas para operações administrativas e migrações.
    """
    
    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset()