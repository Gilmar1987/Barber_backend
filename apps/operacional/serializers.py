# [Domínio: operacional] [Skill: serializer]
"""
📖 MANIFESTO (Skill 04 - View):
"O Serializer do DRF executa a higienização de strings de entrada"

📖 MANIFESTO (Negative Constraints):
"PROIBIDO vazar dicionários primitivos (request.data) para o Service sem
validação prévia por um Serializer fortemente tipado"

 MANIFESTO (Multi-tenancy - US06):
"barbearia_id é injetado pelo Service via JWT, nunca vem do request"

✅ Regras seguidas:
- Serializers validam dados de entrada (DRF)
- Serializers convertem para Pydantic DTOs (to_dto)
- Higienização de dados (remove espaços, normaliza)
- Validações customizadas (preço, comissão, duração)
- Documentação automática via drf-spectacular
"""
from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


# ═══════════════════════════════════════════════════════════
# SERIALIZERS DE SERVIÇO
# ═══════════════════════════════════════════════════════════

class ServicoCreateSerializer(serializers.Serializer):
    """
    Serializer para criação de serviço.
    Higieniza e valida dados antes de converter para DTO.
    """
    nome = serializers.CharField(
        max_length=100,
        min_length=3,
        help_text="Nome legível do serviço (ex: 'Barba Terapia')"
    )
    preco = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text="Preço nominal cobrado (deve ser > 0)"
    )
    duracao_minutos = serializers.IntegerField(
        min_value=5,
        default=30,
        help_text="Bloqueio de tempo na agenda (mínimo 5 minutos)"
    )
    ativo = serializers.BooleanField(
        default=True,
        help_text="Serviço disponível para agendamento"
    )
    
    def validate_nome(self, value: str) -> str:
        """Higieniza o nome do serviço."""
        return value.strip()
    
    def to_dto(self):
        """Converte dados validados para Pydantic DTO."""
        from apps.operacional.dtos import ServicoCreateDTO
        
        return ServicoCreateDTO(
            nome=self.validated_data['nome'],
            preco=self.validated_data['preco'],
            duracao_minutos=self.validated_data.get('duracao_minutos', 30),
            ativo=self.validated_data.get('ativo', True),
        )


class ServicoUpdateSerializer(serializers.Serializer):
    """
    Serializer para atualização parcial de serviço.
    Todos os campos são opcionais.
    """
    nome = serializers.CharField(
        max_length=100,
        min_length=3,
        required=False,
        help_text="Nome legível do serviço"
    )
    preco = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=False,
        help_text="Preço nominal cobrado"
    )
    duracao_minutos = serializers.IntegerField(
        min_value=5,
        required=False,
        help_text="Bloqueio de tempo na agenda"
    )
    ativo = serializers.BooleanField(
        required=False,
        help_text="Serviço disponível para agendamento"
    )
    
    def validate_nome(self, value: str) -> str:
        """Higieniza o nome do serviço."""
        return value.strip()
    
    def to_dto(self):
        """Converte dados validados para Pydantic DTO."""
        from apps.operacional.dtos import ServicoUpdateDTO
        
        return ServicoUpdateDTO(
            nome=self.validated_data.get('nome'),
            preco=self.validated_data.get('preco'),
            duracao_minutos=self.validated_data.get('duracao_minutos'),
            ativo=self.validated_data.get('ativo'),
        )


# ═══════════════════════════════════════════════════════════
# SERIALIZERS DE PROFISSIONAL
# ═══════════════════════════════════════════════════════════

class ProfissionalCreateSerializer(serializers.Serializer):
    """
    Serializer para criação de vínculo profissional.
    Valida se o usuário existe e é do tipo BARBEIRO.
    """
    usuario_id = serializers.UUIDField(
        help_text="UUID do usuário global (deve ser do tipo BARBEIRO)"
    )
    comissao_percentual = serializers.IntegerField(
        min_value=0,
        max_value=100,
        help_text="Porcentagem retida pelo barbeiro (0 a 100)"
    )
    ativo = serializers.BooleanField(
        default=True,
        help_text="Profissional ativo na equipe"
    )
    
    def validate_usuario_id(self, value):
        """
        Valida se o usuário existe e é do tipo BARBEIRO.
        Usa UsuarioRepository para manter isolamento de domínios.
        """
        from apps.core.repository import UsuarioRepository
        usuario = UsuarioRepository.get_by_id_as_barbeiro(value)
        if usuario is None:
            raise serializers.ValidationError(
                'Usuário não encontrado ou não é do tipo BARBEIRO'
            )
        return value
    
    def to_dto(self):
        """Converte dados validados para Pydantic DTO."""
        from apps.operacional.dtos import ProfissionalCreateDTO
        
        return ProfissionalCreateDTO(
            usuario_id=self.validated_data['usuario_id'],
            comissao_percentual=self.validated_data['comissao_percentual'],
            ativo=self.validated_data.get('ativo', True),
        )


class ProfissionalUpdateSerializer(serializers.Serializer):
    """
    Serializer para atualização de vínculo profissional.
    Apenas comissão e status ativo podem ser alterados.
    """
    comissao_percentual = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
        help_text="Porcentagem retida pelo barbeiro (0 a 100)"
    )
    ativo = serializers.BooleanField(
        required=False,
        help_text="Profissional ativo na equipe"
    )
    
    def to_dto(self):
        """Converte dados validados para Pydantic DTO."""
        from apps.operacional.dtos import ProfissionalUpdateDTO
        
        return ProfissionalUpdateDTO(
            comissao_percentual=self.validated_data.get('comissao_percentual'),
            ativo=self.validated_data.get('ativo'),
        )


# ═══════════════════════════════════════════════════════════
# SERIALIZERS DE RESPOSTA (Documentação Swagger)
# ═══════════════════════════════════════════════════════════

class ServicoResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta de serviço (documentação Swagger).
    """
    id = serializers.IntegerField(help_text="ID sequencial interno")
    barbearia_id = serializers.UUIDField(help_text="ID da barbearia (tenant)")
    nome = serializers.CharField(help_text="Nome do serviço")
    preco = serializers.DecimalField(max_digits=10, decimal_places=2)
    duracao_minutos = serializers.IntegerField()
    ativo = serializers.BooleanField()


class ProfissionalResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta de profissional (documentação Swagger).
    """
    id = serializers.IntegerField(help_text="ID sequencial interno")
    barbearia_id = serializers.UUIDField(help_text="ID da barbearia (tenant)")
    usuario_id = serializers.UUIDField(help_text="ID do usuário global")
    usuario_nome = serializers.CharField(help_text="Nome do barbeiro")
    comissao_percentual = serializers.IntegerField()
    ativo = serializers.BooleanField()


# ═══════════════════════════════════════════════════════════
# SERIALIZERS DE GRADE HORÁRIA
# ═══════════════════════════════════════════════════════════

class GradeHorariaCreateSerializer(serializers.Serializer):
    dia_semana = serializers.IntegerField(min_value=0, max_value=6, help_text="0=Domingo, 6=Sábado")
    hora_inicio = serializers.TimeField()
    hora_fim = serializers.TimeField()
    intervalo_inicio = serializers.TimeField(required=False, allow_null=True)
    intervalo_fim = serializers.TimeField(required=False, allow_null=True)
    ativo = serializers.BooleanField(default=True)

    def to_dto(self):
        from apps.operacional.dtos import GradeHorariaCreateDTO
        return GradeHorariaCreateDTO(
            dia_semana=self.validated_data['dia_semana'],
            hora_inicio=self.validated_data['hora_inicio'],
            hora_fim=self.validated_data['hora_fim'],
            intervalo_inicio=self.validated_data.get('intervalo_inicio'),
            intervalo_fim=self.validated_data.get('intervalo_fim'),
            ativo=self.validated_data.get('ativo', True)
        )


class GradeHorariaUpdateSerializer(serializers.Serializer):
    hora_inicio = serializers.TimeField(required=False)
    hora_fim = serializers.TimeField(required=False)
    intervalo_inicio = serializers.TimeField(required=False, allow_null=True)
    intervalo_fim = serializers.TimeField(required=False, allow_null=True)
    ativo = serializers.BooleanField(required=False)

    def to_dto(self):
        from apps.operacional.dtos import GradeHorariaUpdateDTO
        return GradeHorariaUpdateDTO(
            hora_inicio=self.validated_data.get('hora_inicio'),
            hora_fim=self.validated_data.get('hora_fim'),
            intervalo_inicio=self.validated_data.get('intervalo_inicio'),
            intervalo_fim=self.validated_data.get('intervalo_fim'),
            ativo=self.validated_data.get('ativo')
        )


# ═══════════════════════════════════════════════════════════
# SERIALIZERS DE INDISPONIBILIDADES
# ═══════════════════════════════════════════════════════════

class DiaIndisponivelCreateSerializer(serializers.Serializer):
    data = serializers.DateField()
    motivo = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def to_dto(self):
        from apps.operacional.dtos import DiaIndisponivelCreateDTO
        return DiaIndisponivelCreateDTO(
            data=self.validated_data['data'],
            motivo=self.validated_data.get('motivo')
        )


class IntervaloIndisponivelCreateSerializer(serializers.Serializer):
    data = serializers.DateField()
    hora_inicio = serializers.TimeField()
    hora_fim = serializers.TimeField()
    motivo = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def to_dto(self):
        from apps.operacional.dtos import IntervaloIndisponivelCreateDTO
        return IntervaloIndisponivelCreateDTO(
            data=self.validated_data['data'],
            hora_inicio=self.validated_data['hora_inicio'],
            hora_fim=self.validated_data['hora_fim'],
            motivo=self.validated_data.get('motivo')
        )


# ═══════════════════════════════════════════════════════════
# SERIALIZERS DE HABILITAÇÃO SERVIÇO-PROFISSIONAL
# ═══════════════════════════════════════════════════════════

class ServicoProfissionalCreateSerializer(serializers.Serializer):
    servico_id = serializers.IntegerField()
    profissional_id = serializers.IntegerField()
    habilitado = serializers.BooleanField(default=True)

    def to_dto(self):
        from apps.operacional.dtos import ServicoProfissionalCreateDTO
        return ServicoProfissionalCreateDTO(
            servico_id=self.validated_data['servico_id'],
            profissional_id=self.validated_data['profissional_id'],
            habilitado=self.validated_data.get('habilitado', True)
        )


# ═══════════════════════════════════════════════════════════
# SERIALIZERS DE CONVITE PROFISSIONAL (Fluxo Híbrido)
# ═══════════════════════════════════════════════════════════

class ConviteProfissionalCreateSerializer(serializers.Serializer):
    nome_completo = serializers.CharField(max_length=255, min_length=3)
    email = serializers.EmailField()
    cpf = serializers.CharField(max_length=11, min_length=11)
    telefone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    comissao_percentual = serializers.IntegerField(min_value=0, max_value=100)

    def validate_cpf(self, value):
        return ''.join(filter(str.isdigit, value))

    def to_dto(self):
        from apps.operacional.dtos import ConviteProfissionalCreateDTO
        return ConviteProfissionalCreateDTO(
            nome_completo=self.validated_data['nome_completo'].strip(),
            email=self.validated_data['email'].lower().strip(),
            cpf=self.validated_data['cpf'],
            telefone=self.validated_data.get('telefone'),
            comissao_percentual=self.validated_data['comissao_percentual']
        )


class ConviteAceiteSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64)



# ═══════════════════════════════════════════════════════════
# SERIALIZERS DE RESPOSTA (Documentação Swagger)
# ═══════════════════════════════════════════════════════════

class GradeHorariaResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    profissional_id = serializers.IntegerField()
    dia_semana = serializers.IntegerField()
    dia_semana_nome = serializers.CharField()
    hora_inicio = serializers.TimeField()
    hora_fim = serializers.TimeField()
    intervalo_inicio = serializers.TimeField(allow_null=True)
    intervalo_fim = serializers.TimeField(allow_null=True)
    ativo = serializers.BooleanField()


class DiaIndisponivelResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    profissional_id = serializers.IntegerField()
    data = serializers.DateField()
    motivo = serializers.CharField(allow_null=True)
    criado_por_id = serializers.UUIDField(allow_null=True)
    data_criacao = serializers.DateTimeField()


class IntervaloIndisponivelResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    profissional_id = serializers.IntegerField()
    data = serializers.DateField()
    hora_inicio = serializers.TimeField()
    hora_fim = serializers.TimeField()
    motivo = serializers.CharField(allow_null=True)
    criado_por_id = serializers.UUIDField(allow_null=True)
    data_criacao = serializers.DateTimeField()


class ServicoHabilitadoResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    servico_id = serializers.IntegerField()
    servico_nome = serializers.CharField()
    profissional_id = serializers.IntegerField()
    profissional_nome = serializers.CharField()
    habilitado = serializers.BooleanField()
    data_criacao = serializers.DateTimeField()