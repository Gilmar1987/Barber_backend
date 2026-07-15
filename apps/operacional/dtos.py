# [Domínio: operacional] [Skill: dto]
"""
📖 MANIFESTO (Negative Constraints):
"PROIBIDO vazar dicionários primitivos (request.data) para o Service sem
validação prévia por um Serializer fortemente tipado (Type Hints obrigatórios;
Any proibido)."

✅ Regras seguidas:
- Pydantic DTOs para entrada/saída de Services
- Validação forte de tipos (sem Any)
- DTOs específicos para cada caso de uso
- Pydantic v2 (model_config = ConfigDict(from_attributes=True))
- Separação de responsabilidades (barbearia_id é injetado pelo Service)
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ═══════════════════════════════════════════════════════════
# DTOs de SERVIÇO (core_servico)
# ═══════════════════════════════════════════════════════════



class ServicoCreateDTO(BaseModel):
    """DTO para criação de serviço."""
    nome: str = Field(..., min_length=3, max_length=100)
    preco: Decimal = Field(..., gt=0, decimal_places=2)
    duracao_minutos: int = Field(default=30, ge=5)
    ativo: bool = True
    todos_profissionais_habilitados: bool = True
    profissional_ids: Optional[List[int]] = Field(
        default=None,
        description="Lista de IDs de profissionais habilitados (usado quando todos_profissionais_habilitados=False)"
    )
    
    @field_validator('profissional_ids')
    @classmethod
    def validar_profissional_ids(cls, v, info):
        todos_habilitados = info.data.get('todos_profissionais_habilitados', True)
        if not todos_habilitados and (v is None or len(v) == 0):
            raise ValueError(
                'Quando todos_profissionais_habilitados=False, '
                'é obrigatório informar pelo menos um profissional em profissional_ids'
            )
        return v


class ServicoUpdateDTO(BaseModel):
    """DTO para atualização parcial de serviço."""
    nome: Optional[str] = Field(None, min_length=3, max_length=100)
    preco: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    duracao_minutos: Optional[int] = Field(None, ge=5)
    ativo: Optional[bool] = None
    todos_profissionais_habilitados: Optional[bool] = None


class ServicoResponseDTO(BaseModel):
    """DTO de resposta para Serviço."""
    id: int
    barbearia_id: UUID
    nome: str
    preco: Decimal
    duracao_minutos: int
    ativo: bool
    todos_profissionais_habilitados: bool
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════
# DTOs de PROFISSIONAL (core_profissional)
# ═══════════════════════════════════════════════════════════

class ProfissionalCreateDTO(BaseModel):
    """DTO para criação de vínculo profissional."""
    usuario_id: UUID = Field(..., description="UUID do usuário global (tipo BARBEIRO)")
    comissao_percentual: int = Field(..., ge=0, le=100)
    ativo: bool = True


class ProfissionalUpdateDTO(BaseModel):
    """DTO para atualização de vínculo profissional."""
    comissao_percentual: Optional[int] = Field(None, ge=0, le=100)
    ativo: Optional[bool] = None


class ProfissionalResponseDTO(BaseModel):
    """DTO de resposta para Profissional."""
    id: int
    barbearia_id: UUID
    usuario_id: UUID
    usuario_nome: str
    comissao_percentual: int
    ativo: bool
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════
# DTOs de GRADE HORÁRIA (core_gradehoraria)
# ═══════════════════════════════════════════════════════════

class GradeHorariaCreateDTO(BaseModel):
    """DTO para criação de grade horária."""
    dia_semana: int = Field(..., ge=0, le=6, description="0=Domingo, 6=Sábado")
    hora_inicio: time
    hora_fim: time
    intervalo_inicio: Optional[time] = None
    intervalo_fim: Optional[time] = None
    ativo: bool = True
    
    @field_validator('hora_fim')
    @classmethod
    def validar_hora_fim(cls, v: time, info) -> time:
        if 'hora_inicio' in info.data and v <= info.data['hora_inicio']:
            raise ValueError('hora_fim deve ser posterior a hora_inicio')
        return v
    
    @field_validator('intervalo_fim')
    @classmethod
    def validar_intervalo_fim(cls, v: Optional[time], info) -> Optional[time]:
        if v is not None:
            intervalo_inicio = info.data.get('intervalo_inicio')
            if intervalo_inicio is None:
                raise ValueError('intervalo_inicio é obrigatório quando intervalo_fim é informado')
            if v <= intervalo_inicio:
                raise ValueError('intervalo_fim deve ser posterior a intervalo_inicio')
        return v


class GradeHorariaUpdateDTO(BaseModel):
    """DTO para atualização de grade horária."""
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    intervalo_inicio: Optional[time] = None
    intervalo_fim: Optional[time] = None
    ativo: Optional[bool] = None


class GradeHorariaResponseDTO(BaseModel):
    """DTO de resposta para Grade Horária."""
    id: int
    profissional_id: int
    dia_semana: int
    dia_semana_nome: str
    hora_inicio: time
    hora_fim: time
    intervalo_inicio: Optional[time]
    intervalo_fim: Optional[time]
    ativo: bool
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════
# DTOs de INDISPONIBILIDADES
# ═══════════════════════════════════════════════════════════

class DiaIndisponivelCreateDTO(BaseModel):
    """DTO para criação de dia indisponível."""
    data: date
    motivo: Optional[str] = Field(None, max_length=255)


class DiaIndisponivelResponseDTO(BaseModel):
    """DTO de resposta para Dia Indisponível."""
    id: int
    profissional_id: int
    data: date
    motivo: Optional[str]
    criado_por_id: Optional[UUID]
    data_criacao: datetime
    
    model_config = ConfigDict(from_attributes=True)


class IntervaloIndisponivelCreateDTO(BaseModel):
    """DTO para criação de intervalo indisponível."""
    data: date
    hora_inicio: time
    hora_fim: time
    motivo: Optional[str] = Field(None, max_length=255)
    
    @field_validator('hora_fim')
    @classmethod
    def validar_hora_fim(cls, v: time, info) -> time:
        if 'hora_inicio' in info.data and v <= info.data['hora_inicio']:
            raise ValueError('hora_fim deve ser posterior a hora_inicio')
        return v


class IntervaloIndisponivelResponseDTO(BaseModel):
    """DTO de resposta para Intervalo Indisponível."""
    id: int
    profissional_id: int
    data: date
    hora_inicio: time
    hora_fim: time
    motivo: Optional[str]
    criado_por_id: Optional[UUID]
    data_criacao: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════
# DTOs de HABILITAÇÃO SERVIÇO-PROFISSIONAL
# ═══════════════════════════════════════════════════════════

class ServicoProfissionalCreateDTO(BaseModel):
    """DTO para criação de vínculo serviço-profissional."""
    servico_id: int
    profissional_id: int
    habilitado: bool = True


class ServicoHabilitadoResponseDTO(BaseModel):
    """DTO de resposta para habilitação serviço-profissional."""
    id: int
    servico_id: int
    servico_nome: str
    profissional_id: int
    profissional_nome: str
    habilitado: bool
    data_criacao: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════
# DTOs de CONVITE PROFISSIONAL (Fluxo Híbrido)
# ═══════════════════════════════════════════════════════════

class ConviteProfissionalCreateDTO(BaseModel):
    """DTO para criação de convite profissional (fluxo híbrido)."""
    nome_completo: str = Field(..., min_length=3, max_length=255)
    email: str = Field(..., max_length=254)
    cpf: str = Field(..., min_length=11, max_length=11)
    telefone: Optional[str] = Field(None, max_length=15)
    comissao_percentual: int = Field(..., ge=0, le=100)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v or '.' not in v:
            raise ValueError('Email inválido')
        return v.lower().strip()
    
    @field_validator('cpf')
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) != 11:
            raise ValueError('CPF deve ter exatamente 11 dígitos')
        return cleaned
    
    @field_validator('nome_completo')
    @classmethod
    def validate_nome(cls, v: str) -> str:
        return v.strip()


class ConviteProfissionalResponseDTO(BaseModel):
    """DTO de resposta para convite profissional."""
    id: int
    barbearia_id: UUID
    usuario_id: UUID
    nome_completo: str
    email: str
    cpf: str
    telefone: Optional[str]
    comissao_percentual: int
    status: str
    data_criacao: datetime
    data_expiracao: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ConviteAceiteResponseDTO(BaseModel):
    """DTO de resposta após aceitação de convite."""
    success: bool
    message: str
    profissional_id: Optional[int] = None
    barbearia_id: Optional[UUID] = None


# ═══════════════════════════════════════════════════════════
# DTOs de RESULTADO (Service Results) — TIPADOS
# ═══════════════════════════════════════════════════════════

# Define Union de todos os DTOs de resposta possíveis
ResponseDTOType = Union[
    ServicoResponseDTO,
    ProfissionalResponseDTO,
    GradeHorariaResponseDTO,
    DiaIndisponivelResponseDTO,
    IntervaloIndisponivelResponseDTO,
    ServicoHabilitadoResponseDTO,
    ConviteProfissionalResponseDTO,
    ConviteAceiteResponseDTO,
]


class ServiceResultSingleDTO(BaseModel):
    """DTO para resultado de operações que retornam um único objeto."""
    success: bool
    data: Optional[ResponseDTOType] = None
    error: Optional[str] = None
    message: Optional[str] = None
    details: Optional[dict] = None


class ServiceResultListDTO(BaseModel):
    """DTO para resultado de operações que retornam uma lista."""
    success: bool
    data: Optional[List[ResponseDTOType]] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class ServiceResultMessageDTO(BaseModel):
    """DTO para resultado de operações que retornam apenas mensagens."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None