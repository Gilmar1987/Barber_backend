# apps/agenda/dtos.py
from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel, Field

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