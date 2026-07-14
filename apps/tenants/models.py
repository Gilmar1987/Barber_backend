
# [Domínio: tenants] [Skill: model]
"""
📖 MANIFESTO (Geolocalização):
"CRÍTICO: Usar GEOGRAPHY, não GEOMETRY"
"GEOGRAPHY calcula em metros reais"

✅ Regras seguidas:
- UUID como primary key (segurança em URLs)
- CNPJ único e indexado
- GEOGRAPHY(Point, 4326) para cálculos em metros reais
- Trilha de auditoria completa
- Soft delete (is_deleted, deleted_at, deleted_by)
"""
import uuid
from typing import Optional
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models

from common.managers import UnscopedManager


class Barbearia(models.Model):
    objects = models.Manager()
    unscoped_objects = UnscopedManager()

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Identificador único da barbearia (tenant_id)"
    )
    nome_comercial = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        help_text="Nome comercial da barbearia"
    )
    cnpj = models.CharField(
        max_length=14,
        unique=True,
        null=False,
        blank=False,
        db_index=True,
        help_text="CNPJ da barbearia (apenas 14 números)"
    )
    cep = models.CharField(
        max_length=8,
        null=False,
        blank=False,
        help_text="CEP da barbearia (apenas 8 números)"
    )
    logradouro = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        help_text="Endereço completo da barbearia"
    )
    numero = models.CharField(
        max_length=10,
        null=False,
        blank=False,
        help_text="Número do endereço"
    )
    complemento = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Complemento do endereço (sala, andar, etc.)"
    )
    bairro = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        help_text="Bairro da barbearia"
    )
    cidade = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        help_text="Cidade da barbearia"
    )
    estado = models.CharField(
        max_length=2,
        null=False,
        blank=False,
        help_text="Estado da barbearia (sigla Ex: PE, SP, RJ)"
    )
    
    # ✅ CAMPO POSTGIS RESTAURADO (Essencial para US01 - Busca por Proximidade)
    localizacao = gis_models.PointField(
        geography=True,  # ✅ GEOGRAPHY calcula em metros reais
        srid=4326,
        null=True,
        blank=True,
        help_text="Ponto geométrico geoespacial (Longitude, Latitude)"
    )

    telefone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        help_text="Telefone comercial da barbearia"
    )
    email = models.EmailField(
        null=False,
        blank=False,
        help_text="Email comercial da barbearia"
    )
    ativo = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Indica se a barbearia está ativa"
    )

    # Configuração operacional padrão
    balanceamento_minutos = models.IntegerField(
        default=60,
        help_text="Minutos antes do intervalo para encaixar agendamentos curtos (máx 60)"
    )
    buffer_minutos = models.IntegerField(
        default=0,
        help_text="Minutos de buffer entre agendamentos (tempo de limpeza/preparação)"
    )
    slot_padrao_minutos = models.IntegerField(
        default=30,
        help_text="Duração padrão do slot de agendamento em minutos"
    )

    # Trilha de auditoria
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp de criação")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp de atualização")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='created_barbearias',
        on_delete=models.SET_NULL, help_text="Usuário que criou o registro"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='updated_barbearias',
        on_delete=models.SET_NULL, help_text="Usuário que atualizou o registro"
    )

    # Soft Delete
    is_deleted = models.BooleanField(default=False, db_index=True, help_text="Indica se o registro foi soft deleted")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp do delete")
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='deleted_barbearias',
        on_delete=models.SET_NULL, help_text="Usuário que deletou o registro"
    )

    class Meta:
        verbose_name = "Barbearia"
        verbose_name_plural = "Barbearias"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cnpj'], name='idx_barbearia_cnpj'),
            models.Index(fields=['ativo', 'is_deleted'], name='idx_barbearia_ativo'),
            models.Index(fields=['cidade', 'estado'], name='idx_barbearia_cidade_estado'),
            models.Index(fields=['created_at'], name='idx_barbearia_created_at'),
            # Índice GIST para consultas espaciais rápidas (US01)
            gis_models.Index(fields=['localizacao'], name='idx_barbearia_localizacao'),
        ]

    def __str__(self) -> str:
        return f"{self.nome_comercial} ({self.cidade}/{self.estado})"
    
    def get_cnpj_masked(self) -> str:
        if self.cnpj and len(self.cnpj) >= 2:
            return f"{self.cnpj[:2]}.***.***{self.cnpj[-1]}"
        return "**.***.***"

    def get_endereco_completo(self) -> str:
        partes = [self.logradouro, self.numero, self.complemento, self.bairro, f"{self.cidade}/{self.estado}", self.cep]
        return ", ".join(parte for parte in partes if parte)

    def soft_delete(self, user_id: Optional[uuid.UUID] = None) -> None:
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user_id:
            self.deleted_by_id = user_id
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])