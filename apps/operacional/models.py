# [Domínio: operacional] [Skill: model]
"""
📖 MANIFESTO (Modelo de Dados Físico - Documento 3):
"Tabela core_servico: Portfólio de serviços amarrado ao Tenant."
"Tabela core_profissional: Folha contratual do barbeiro parceiro."

✅ Regras seguidas:
- BIGSERIAL como PK (conforme PDF)
- db_table explícito (core_servico, core_profissional)
- FK para Barbearia (Multi-tenancy)
- Validação de comissão (0 a 100)
- Campo 'ativo' para gestão de disponibilidade
- AbstractTimestampedModel: trilha de auditoria (created_at, updated_at, created_by, updated_by)
- ForeignKey + unique_together: suporte ao modelo freelancer (múltiplas barbearias)
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.tenants.models import Barbearia
from common.models import AbstractTimestampedModel


class Servico(AbstractTimestampedModel):
    """
    Tabela: core_servico
    Portfólio de serviços disponíveis em cada barbearia.
    """
    id = models.BigAutoField(primary_key=True)
    
    barbearia = models.ForeignKey(
        Barbearia,
        on_delete=models.CASCADE,
        related_name='servicos'
    )
    
    nome = models.CharField(max_length=100, help_text="Nome legível (ex: 'Barba Terapia')")
    preco = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço nominal cobrado")
    duracao_minutos = models.IntegerField(default=30, help_text="Bloqueio de tempo na agenda")
    ativo = models.BooleanField(default=True, help_text="Serviço disponível para agendamento")

    class Meta:
        db_table = 'core_servico'
        indexes = [
            models.Index(fields=['barbearia'], name='idx_servico_barbearia'),
        ]
        verbose_name = "Serviço"
        verbose_name_plural = "Serviços"

    def __str__(self):
        return f"{self.nome} ({self.barbearia.nome_comercial})"


class Profissional(AbstractTimestampedModel):
    """
    Tabela: core_profissional
    Folha contratual do barbeiro parceiro.
    ForeignKey + unique_together: suporta modelo freelancer (múltiplas barbearias).
    """
    id = models.BigAutoField(primary_key=True)
    
    barbearia = models.ForeignKey(
        Barbearia,
        on_delete=models.CASCADE,
        related_name='profissionais'
    )
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vinculos_profissional'
    )
    
    comissao_percentual = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentagem retida pelo barbeiro (0 a 100)"
    )
    ativo = models.BooleanField(default=True, help_text="Profissional ativo na equipe")

    class Meta:
        db_table = 'core_profissional'
        unique_together = [('usuario', 'barbearia')]  # Freelancer: 1 vínculo por barbearia
        indexes = [
            models.Index(fields=['usuario'], name='idx_profissional_usuario'),
            models.Index(fields=['barbearia'], name='idx_profissional_barbearia'),
        ]
        verbose_name = "Profissional"
        verbose_name_plural = "Profissionais"

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} ({self.barbearia.nome_comercial})"