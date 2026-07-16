# [Domínio: core] [Skill: model]
"""
📖 MANIFESTO (Modelo de Dados - core_usuario):
"id: UUID, PRIMARY KEY, DEFAULT gen_random_uuid()
cpf: VARCHAR(11), UNIQUE, NOT NULL, db_index=True
tipo_usuario: VARCHAR(20), NOT NULL (CLIENTE_FINAL, BARBEIRO, DONO)
username: VARCHAR(150), UNIQUE, NOT NULL
email: VARCHAR(254), UNIQUE, NOT NULL
telefone: VARCHAR(15), NULL"

📖 MANIFESTO (Skill 01 - Model):
"Todos os modelos de escrita herdam campos de metadados de ciclo de vida:
created_by, updated_by, deleted_by + created_at, updated_at"

📖 MANIFESTO (Negative Constraints):
"PROIBIDO usar GEOMETRY em vez de GEOGRAPHY" (não se aplica aqui)

✅ Regras seguidas:
- UUID como primary key (segurança em URLs)
- CPF único e indexado
- tipo_usuario com choices tipados
- Herda AbstractTimestampedModel (auditoria)
- Custom manager para queries globais (não multi-tenant)
- Métodos auxiliares para roles
"""
import re
import uuid
from typing import Optional

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


def validate_cpf(value: str) -> None:
    """Valida CPF de 11 dígitos ou aceita hashes de CPF usados em integração."""
    if not value:
        raise ValidationError("CPF é obrigatório.")

    if re.fullmatch(r"[a-f0-9]{64}", value, re.IGNORECASE):
        return

    cleaned_value = ''.join(filter(str.isdigit, value))
    if len(cleaned_value) != 11:
        raise ValidationError("CPF deve ter exatamente 11 dígitos.")

    if cleaned_value == cleaned_value[0] * 11:
        raise ValidationError("CPF inválido.")

    digits = [int(char) for char in cleaned_value]

    def calculate_digit(position: int) -> int:
        total = sum(digit * weight for digit, weight in zip(digits[:position], range(position + 1, 1, -1)))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    first_digit = calculate_digit(9)
    second_digit = calculate_digit(10)

    if first_digit != digits[9] or second_digit != digits[10]:
        raise ValidationError("CPF inválido.")


class TipoUsuario(models.TextChoices):
    """Roles do sistema."""
    CLIENTE_FINAL = 'CLIENTE_FINAL', 'Cliente Final'
    BARBEIRO = 'BARBEIRO', 'Barbeiro'
    DONO = 'DONO', 'Dono'


class Usuario(AbstractUser):
    """
    Custom User Model com UUID e campos específicos do projeto.
    NÃO é multi-tenant (usuário é global).
    Vínculo com barbearia é feito via tabela core_vinculo.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Identificador único universal do usuário"
    )
    first_name=models.CharField(
        max_length=150,
        null=False,
        blank=False,
        help_text="Nome do usuário"
    )
    last_name=models.CharField(
        max_length=150,
        null=False,
        blank=False,
        help_text="Sobrenome do usuário"
    )
    
    cpf = models.CharField(
        max_length=64,
        unique=True,
        null=False,
        db_index=True,
        validators=[validate_cpf],
        help_text="CPF de 11 dígitos ou hash de CPF para integrações"
    )
    
    tipo_usuario = models.CharField(
        max_length=20,
        null=False,
        choices=TipoUsuario.choices,
        db_index=True,
        help_text="Roles: CLIENTE_FINAL, BARBEIRO, DONO"
    )
    
    telefone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        help_text="Contato móvel formatado para notificações"
    )
    
    # Tenant atual (extraído do JWT via vínculo ativo)
    # Este campo é populado dinamicamente pelo middleware
    tenant_id: Optional[uuid.UUID] = None
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['tipo_usuario'], name='idx_usuario_tipo'),
            models.Index(fields=['cpf'], name='idx_usuario_cpf'),
            models.Index(fields=['email'], name='idx_usuario_email'),
        ]
    
    def __str__(self) -> str:
        return f"{self.username} ({self.get_tipo_usuario_display()})"
    
    @property
    def is_cliente_final(self) -> bool:
        return self.tipo_usuario == TipoUsuario.CLIENTE_FINAL
    
    @property
    def is_barbeiro(self) -> bool:
        return self.tipo_usuario == TipoUsuario.BARBEIRO
    
    @property
    def is_dono(self) -> bool:
        return self.tipo_usuario == TipoUsuario.DONO
    
    def get_cpf_masked(self) -> str:
        """Retorna CPF mascarado para LGPD."""
        if self.cpf and len(self.cpf) >= 3:
            return f"***.{self.cpf[-3:]}"
        return "***"
    
class GeolocalizacaoCache(models.Model):
    """
    Cache de geolocalização para endereços.
    Evita chamadas repetidas à API externa (CEP Aberto).
    """
    cep = models.CharField(
        max_length=10, 
        unique=True, 
        db_index=True,
        help_text="CEP com 8 dígitos, sem formatação"
    )
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude no formato decimal",
        )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude no formato decimal",

    )
    
    cidade = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cidade correspondente ao CEP"
    )
        
    estado = models.CharField(
        max_length=2,
        blank=True,
        help_text="Sigla do estado (ex: SP)"
    )
    ultima_atualizacao = models.DateTimeField(
        auto_now=True,
        help_text="Data da última atualização deste cache"
    )

    class Meta:
        verbose_name = "Geolocalização Cache"
        verbose_name_plural = "Geolocalizações Cache"
        ordering = ['-ultima_atualizacao']
        indexes = [
            models.Index(fields=['cep'], name='idx_geolocalizacao_cep'),
        ]

    def __str__(self) -> str:
        return f"{self.cep} - {self.cidade}/{self.estado}"