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
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
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
    # Lacuna 3: Opção de direcionar para todos os profissionais
    todos_profissionais_habilitados = models.BooleanField(
    default=True,
    help_text="Se SIM, todos os profissionais da barbearia podem realizar este serviço. Se NÃO, o DONO seleciona manualmente."
)
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
    
# [Domínio: operacional] [Skill: model]
"""


✅ Regras seguidas:
- BIGSERIAL como PK (conforme padrão do domínio)
- FK para Barbearia (Multi-tenancy)
- FK para Usuario (identidade global)
- Token único para aceitação (segurança)
- Expira em 7 dias (governança)
"""



class ConviteProfissional(models.Model):
    """
    Tabela: core_conviteprofissional
    Armazena convites pendentes de vínculo profissional.
    """
    STATUS_PENDENTE = 'PENDENTE'
    STATUS_ACEITO = 'ACEITO'
    STATUS_RECUSADO = 'RECUSADO'
    STATUS_EXPIRADO = 'EXPIRADO'
    
    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Pendente'),
        (STATUS_ACEITO, 'Aceito'),
        (STATUS_RECUSADO, 'Recusado'),
        (STATUS_EXPIRADO, 'Expirado'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    
    # Vínculo obrigatório com o Tenant (Isolamento Multi-tenant)
    barbearia = models.ForeignKey(
        Barbearia,
        on_delete=models.CASCADE,
        related_name='convites_profissionais'
    )
    
    # Usuário convidado (pode ser existente ou criado no momento do convite)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='convites_recebidos'
    )
    
    # Dados do convite
    nome_completo = models.CharField(max_length=255, help_text="Nome completo do barbeiro")
    email = models.EmailField(help_text="Email para envio do convite")
    cpf = models.CharField(max_length=11, help_text="CPF do barbeiro (apenas números)")
    telefone = models.CharField(max_length=15, blank=True, null=True)
    comissao_percentual = models.IntegerField(help_text="Comissão oferecida (0-100)")
    
    # Status e controle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    token = models.CharField(max_length=64, unique=True, help_text="Token único para aceitação")
    
    # Trilha de auditoria
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='convites_enviados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_expiracao = models.DateTimeField(help_text="Convite expira em 7 dias")
    data_resposta = models.DateTimeField(null=True, blank=True, help_text="Quando o barbeiro aceitou/recusou")
    
    class Meta:
        db_table = 'core_conviteprofissional'
        indexes = [
            models.Index(fields=['barbearia', 'status'], name='idx_convite_barbearia_status'),
            models.Index(fields=['token'], name='idx_convite_token'),
            models.Index(fields=['email'], name='idx_convite_email'),
        ]
        verbose_name = "Convite Profissional"
        verbose_name_plural = "Convites Profissionais"
    
    def __str__(self):
        return f"Convite para {self.nome_completo} ({self.barbearia.nome_comercial})"
    
    def save(self, *args, **kwargs):
        # Gera token único se não existir
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        
        # Define data de expiração (7 dias)
        if not self.data_expiracao:
            self.data_expiracao = timezone.now() + timedelta(days=7)
        
        super().save(*args, **kwargs)
    
    def is_valido(self):
        """Verifica se o convite ainda é válido."""
        return self.status == self.STATUS_PENDENTE and self.data_expiracao > timezone.now()
    
    def aceitar(self):
        """Marca o convite como aceito."""
        self.status = self.STATUS_ACEITO
        self.data_resposta = timezone.now()
        self.save(update_fields=['status', 'data_resposta'])
    
    def recusar(self):
        """Marca o convite como recusado."""
        self.status = self.STATUS_RECUSADO
        self.data_resposta = timezone.now()
        self.save(update_fields=['status', 'data_resposta'])

# ═══════════════════════════════════════════════════════════
# GRADE HORÁRIA DO PROFISSIONAL
# ═══════════════════════════════════════════════════════════

class GradeHoraria(models.Model):
    """
    Tabela: core_gradehoraria
    Define o horário de trabalho do profissional por dia da semana.
    Um profissional pode ter grades diferentes em barbearias diferentes (freelancer).
    """
    DIAS_SEMANA = [
        (0, 'Domingo'),
        (1, 'Segunda-feira'),
        (2, 'Terça-feira'),
        (3, 'Quarta-feira'),
        (4, 'Quinta-feira'),
        (5, 'Sexta-feira'),
        (6, 'Sábado'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name='grades_horarias'
    )
    
    dia_semana = models.IntegerField(
        choices=DIAS_SEMANA,
        help_text="0=Domingo, 6=Sábado"
    )
    
    hora_inicio = models.TimeField(help_text="Início da jornada (ex: 09:00)")
    hora_fim = models.TimeField(help_text="Término da jornada (ex: 18:00)")
    
    # Intervalo de almoço/descanso (opcional)
    intervalo_inicio = models.TimeField(
        null=True, blank=True,
        help_text="Início do intervalo (ex: 12:00)"
    )
    intervalo_fim = models.TimeField(
        null=True, blank=True,
        help_text="Término do intervalo (ex: 13:00)"
    )
    
    ativo = models.BooleanField(
        default=True,
        help_text="Se False, o profissional não trabalha neste dia (folga)"
    )
    
    class Meta:
        db_table = 'core_gradehoraria'
        unique_together = [('profissional', 'dia_semana')]
        indexes = [
            models.Index(fields=['profissional', 'ativo'], name='idx_grade_profissional_ativo'),
        ]
        verbose_name = "Grade Horária"
        verbose_name_plural = "Grades Horárias"
        ordering = ['dia_semana']
    
    def __str__(self):
        status = "✓" if self.ativo else "✗"
        return f"{self.profissional} - {self.get_dia_semana_display()} {status} ({self.hora_inicio}-{self.hora_fim})"


# ═══════════════════════════════════════════════════════════
# DIA INDISPONÍVEL (FOLGAS E EXCEÇÕES)
# ═══════════════════════════════════════════════════════════

class DiaIndisponivel(models.Model):
    """
    Tabela: core_diaindisponivel
    Marca dias específicos em que o profissional não trabalha.
    Ex: Férias, folgas pessoais, feriados.
    """
    id = models.BigAutoField(primary_key=True)
    
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name='dias_indisponiveis'
    )
    
    data = models.DateField(help_text="Data específica de indisponibilidade")
    motivo = models.CharField(
        max_length=255,
        blank=True,
        help_text="Ex: 'Férias', 'Folga pessoal', 'Compromisso'"
    )
    
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='dias_indisponiveis_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_diaindisponivel'
        unique_together = [('profissional', 'data')]
        verbose_name = "Dia Indisponível"
        verbose_name_plural = "Dias Indisponíveis"
        ordering = ['data']
    
    def __str__(self):
        return f"{self.profissional} - {self.data} ({self.motivo or 'Sem motivo'})"


# ═══════════════════════════════════════════════════════════
# INTERVALO INDISPONÍVEL (BLOQUEIOS DE HORÁRIO)
# ═══════════════════════════════════════════════════════════

class IntervaloIndisponivel(models.Model):
    """
    Tabela: core_intervaloindisponivel
    Bloqueia intervalos específicos de horário em uma data.
    Ex: Reunião, compromisso pessoal, manutenção.
    """
    id = models.BigAutoField(primary_key=True)
    
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name='intervalos_indisponiveis'
    )
    
    data = models.DateField(help_text="Data do bloqueio")
    hora_inicio = models.TimeField(help_text="Início do bloqueio")
    hora_fim = models.TimeField(help_text="Término do bloqueio")
    
    motivo = models.CharField(
        max_length=255,
        blank=True,
        help_text="Ex: 'Reunião', 'Compromisso pessoal'"
    )
    
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='intervalos_indisponiveis_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_intervaloindisponivel'
        indexes = [
            models.Index(fields=['profissional', 'data'], name='idx_intervalo_prof_data'),
        ]
        verbose_name = "Intervalo Indisponível"
        verbose_name_plural = "Intervalos Indisponíveis"
        ordering = ['data', 'hora_inicio']
    
    def __str__(self):
        return f"{self.profissional} - {self.data} {self.hora_inicio}-{self.hora_fim}"


# ═══════════════════════════════════════════════════════════
# VÍNCULO SERVIÇO ↔ PROFISSIONAL (Habilitação)
# ═══════════════════════════════════════════════════════════

class ServicoProfissional(models.Model):
    """
    Tabela: core_servicoprofissional
    Vínculo N:N entre serviço e profissional.
    Define quais profissionais estão habilitados para cada serviço.
    
    Regra: Se Servico.todos_profissionais_habilitados = True,
    este registro não é necessário (todos são habilitados automaticamente).
    """
    id = models.BigAutoField(primary_key=True)
    
    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name='profissionais_habilitados'
    )
    
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name='servicos_habilitados'
    )
    
    habilitado = models.BooleanField(
        default=True,
        help_text="Se False, o profissional não pode realizar este serviço"
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_servicoprofissional'
        unique_together = [('servico', 'profissional')]
        verbose_name = "Habilitação de Serviço"
        verbose_name_plural = "Habilitações de Serviço"
    
    def __str__(self):
        status = "✓" if self.habilitado else "✗"
        return f"{self.servico.nome} → {self.profissional} [{status}]"


