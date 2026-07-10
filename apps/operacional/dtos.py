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
- Separação de responsabilidades (barbearia_id é injetado pelo Service, não pelo DTO)
"""
from decimal import Decimal
from typing import Optional, List, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════
# DTOs de SERVIÇO (core_servico)
# ═══════════════════════════════════════════════════════════

class ServicoCreateDTO(BaseModel):
    """DTO para criação de serviço."""
    nome: str = Field(..., min_length=3, max_length=100)
    preco: Decimal = Field(..., gt=0, decimal_places=2)
    duracao_minutos: int = Field(default=30, ge=5)
    ativo: bool = True


class ServicoUpdateDTO(BaseModel):
    """DTO para atualização parcial de serviço."""
    nome: Optional[str] = Field(None, min_length=3, max_length=100)
    preco: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    duracao_minutos: Optional[int] = Field(None, ge=5)
    ativo: Optional[bool] = None


class ServicoResponseDTO(BaseModel):
    """DTO de resposta para Serviço."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    barbearia_id: UUID
    nome: str
    preco: Decimal
    duracao_minutos: int
    ativo: bool


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    barbearia_id: UUID
    usuario_id: UUID
    usuario_nome: str
    comissao_percentual: int
    ativo: bool


# ═══════════════════════════════════════════════════════════
# DTOs de RESULTADO (Service Results)
# ═══════════════════════════════════════════════════════════

class ServiceResultSingleDTO(BaseModel):
    """DTO para resultado de operações que retornam um único objeto."""
    success: bool
    data: Optional[Union[ServicoResponseDTO, ProfissionalResponseDTO]] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class ServiceResultListDTO(BaseModel):
    """DTO para resultado de operações que retornam uma lista."""
    success: bool
    data: List[Union[ServicoResponseDTO, ProfissionalResponseDTO]] = []
    error: Optional[str] = None
    details: Optional[dict] = None


class ServiceResultMessageDTO(BaseModel):
    """DTO para resultado de operações que retornam apenas mensagens."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None