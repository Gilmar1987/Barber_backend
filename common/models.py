# [Domínio: core] [Skill: model]
"""
📖 MANIFESTO (Skill 01 - Model):
"Todos os modelos de escrita herdam campos de metadados de ciclo de vida:
created_by, updated_by, deleted_by (para soft delete) além de carimbos
de data/hora (created_at, updated_at)."

📖 MANIFESTO (Seção 1 - Isolamento Multi-Tenant):
"Os modelos herdam de um TenantBaseModel cujo manager customizado
(TenantManager) estende um TenantQuerySet que injeta automaticamente
o filtro WHERE tenant_id = X."

✅ Regras seguidas:
- UUID como primary key (segurança em URLs)
- tenant_id indexado (performance)
- Trilha de auditoria completa (created_by, updated_by)
- Timestamps automáticos (created_at, updated_at)
- Soft delete via is_deleted + deleted_at
- TenantManager como manager padrão
- unscoped_objects para escape explícito
"""
import uuid
from typing import Optional

from django.conf import settings
from django.db import models

from common.managers import TenantManager, UnscopedManager


class AbstractTimestampedModel(models.Model):
    """
    Modelo abstrato com timestamps e trilha de auditoria.
    NÃO aplica filtro de tenant (use para modelos globais como Usuario).
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Identificador único universal"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Data/hora de criação"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Data/hora da última atualização"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        on_delete=models.SET_NULL,
        help_text="Usuário que criou o registro"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        on_delete=models.SET_NULL,
        help_text="Usuário que atualizou o registro"
    )
    
    class Meta:
        abstract = True


class TenantBaseModel(models.Model):
    """
    Modelo base para entidades multi-tenant com auditoria completa.
    Aplica filtro automático de tenant via TenantManager.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Identificador único universal"
    )
    tenant_id = models.UUIDField(
        db_index=True,
        help_text="ID do tenant (barbearia) - isolamento lógico"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Data/hora de criação"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Data/hora da última atualização"
    )
    created_by = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID do usuário que criou o registro"
    )
    updated_by = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID do usuário que atualizou o registro"
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete - registro marcado como excluído"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora da exclusão lógica"
    )
    deleted_by = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID do usuário que excluiu o registro"
    )
    
    # Managers
    objects = TenantManager()            # Filtro automático de tenant
    unscoped_objects = UnscopedManager() # Escape explícito (uso restrito)
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['tenant_id', 'created_at']),
            models.Index(fields=['tenant_id', 'is_deleted']),
        ]
    
    def soft_delete(self, user_id: Optional[uuid.UUID] = None) -> None:
        """Marca o registro como excluído (soft delete)."""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user_id
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])