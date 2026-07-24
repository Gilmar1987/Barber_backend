# apps/agenda/dtos.py
from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID

class DisponibilidadeSearchDTO(BaseModel):
    """DTO de entrada para busca de disponibilidade."""
    profissional_id: int = Field(..., ge=1, description="ID do profissional")
    servico_id: int = Field(..., ge=1, description="ID do serviço")
    data_inicio: date = Field(..., description="Data inicial (formato: YYYY-MM-DD)")
    data_fim: Optional[date] = Field(None, description="Data final (padrão: data_inicio + 5 dias)")

class SlotDisponivelDTO(BaseModel):
    """DTO de saída para um slot de horário disponível."""
    data: date
    horario_inicio: time
    horario_fim: time

class DisponibilidadeResponseDTO(BaseModel):
    """DTO de resposta padrão."""
    success: bool
    data: List[SlotDisponivelDTO]
    error: Optional[str] = None
    details: Optional[dict] = None




class AgendamentoCreateDTO(BaseModel):
    barbearia_id: UUID = Field(..., description="ID da barbearia")
    profissional_id: int = Field(..., ge=1, description="ID do profissional")
    servico_id: int = Field(..., ge=1, description="ID do serviço")
    data: date = Field(..., description="Data do agendamento (formato: YYYY-MM-DD)")
    hora_inicio: time = Field(..., description="Horário de início do agendamento (formato: HH:MM)")
    nome_cliente: str = Field(..., min_length=3)
    telefone_cliente: str = Field(..., min_length=8)
    observacoes: Optional[str] = None

class AgendamentoResponseDTO(BaseModel):
    id: int
    barbearia_id: UUID
    profissional_nome: str
    servico_nome: str
    data: date
    hora_inicio: time
    hora_fim: time
    status: str
    nome_cliente: str


class AgendamentoClienteResponseDTO(BaseModel):
    id: int
    barbearia_nome:str
    profissional_nome: str
    servico_nome: str
    data: date
    hora_inicio: time
    hora_fim: time
    status: str
    observacoes:Optional[str] = None

class ServiceResultListDTO(BaseModel):
    success: bool
    data: Optional[List[AgendamentoClienteResponseDTO]] = None
    error: Optional[str] = None
    details: Optional[dict] = None

class ServiceResultMessageDTO(BaseModel):
    success: bool
    message: Optional[str] = None
    details: Optional[dict] = None