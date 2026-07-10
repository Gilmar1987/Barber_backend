# [Domínio: tenants] [Skill: dto]
"""
📖 MANIFESTO (Negative Constraints):
"PROIBIDO vazar dicionários primitivos (request.data) para o Service sem
validação prévia por um Serializer fortemente tipado (Type Hints obrigatórios;
Any proibido)."

📖 MANIFESTO (Geolocalização):
"Usar GEOGRAPHY(Point, 4326) para cálculos em metros reais"

📖 MANIFESTO (LGPD Compliance):
"dados sensíveis mascarados em logs e respostas"

✅ Regras seguidas:
- Pydantic DTOs para entrada/saída de Services
- Validação forte de tipos (sem Any)
- Validações customizadas (CNPJ, CEP, coordenadas)
- DTOs específicos para cada caso de uso (Create, Update, Response, List)
- CNPJ mascarado na resposta (LGPD)
- email obrigatório no CreateDTO (alinhado com model null=False, blank=False)
- campos de auditoria alinhados com model (created_at, updated_at)
- is_deleted exposto no ResponseDTO (soft delete visível)
"""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ═══════════════════════════════════════════════════════════
# DTOs DE ENTRADA (Input)
# ═══════════════════════════════════════════════════════════

class BarbeariaCreateDTO(BaseModel):
    """
    DTO para criação de barbearia.
    Valida todos os campos obrigatórios e regras de negócio.
    email obrigatório: alinhado com model (null=False, blank=False).
    """
    nome_comercial: str = Field(..., min_length=1, max_length=255)
    cnpj: str = Field(..., min_length=14)
    cep: str = Field(..., min_length=8, max_length=8)
    logradouro: str = Field(..., min_length=1, max_length=255)
    numero: str = Field(..., min_length=1, max_length=10)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: str = Field(..., min_length=1, max_length=100)
    cidade: str = Field(..., min_length=1, max_length=100)
    estado: str = Field(..., min_length=2, max_length=2)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    telefone: Optional[str] = Field(None, max_length=15)
    email: EmailStr  # obrigatório — model: null=False, blank=False

    @field_validator('cnpj')
    @classmethod
    def validate_cnpj(cls, value: str) -> str:
        cleaned = ''.join(filter(str.isdigit, value))
        if len(cleaned) != 14:
            raise ValueError('CNPJ deve conter exatamente 14 dígitos numéricos')
        return cleaned

    @field_validator('cep')
    @classmethod
    def validate_cep(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError('CEP deve conter apenas números')
        return value

    @field_validator('estado')
    @classmethod
    def validate_estado(cls, value: str) -> str:
        if not (value.isalpha() and len(value) == 2 and value.isupper()):
            raise ValueError('Estado deve ter exatamente 2 letras maiúsculas')
        return value

    @field_validator('telefone')
    @classmethod
    def validate_telefone(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.isdigit():
            raise ValueError('Telefone deve conter apenas números')
        return value


class BarbeariaUpdateDTO(BaseModel):
    """
    DTO para atualização de barbearia.
    Todos os campos são opcionais. CNPJ não é atualizável (imutável por natureza).
    """
    nome_comercial: Optional[str] = Field(None, min_length=1, max_length=255)
    cep: Optional[str] = Field(None, min_length=8, max_length=8)
    logradouro: Optional[str] = Field(None, min_length=1, max_length=255)
    numero: Optional[str] = Field(None, min_length=1, max_length=10)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: Optional[str] = Field(None, min_length=1, max_length=100)
    cidade: Optional[str] = Field(None, min_length=1, max_length=100)
    estado: Optional[str] = Field(None, min_length=2, max_length=2)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    telefone: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    ativo: Optional[bool] = None

    @field_validator('cep')
    @classmethod
    def validate_cep(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.isdigit():
            raise ValueError('CEP deve conter apenas números')
        return value

    @field_validator('estado')
    @classmethod
    def validate_estado(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not (value.isalpha() and len(value) == 2 and value.isupper()):
            raise ValueError('Estado deve ter exatamente 2 letras maiúsculas')
        return value

    @field_validator('telefone')
    @classmethod
    def validate_telefone(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.isdigit():
            raise ValueError('Telefone deve conter apenas números')
        return value


# ═══════════════════════════════════════════════════════════
# DTOs DE SAÍDA (Output)
# ═══════════════════════════════════════════════════════════

class BarbeariaResponseDTO(BaseModel):
    """
    DTO para resposta de barbearia (não expõe dados sensíveis).
    Campos de auditoria alinhados com model: created_at, updated_at.
    is_deleted exposto para refletir estado de soft delete.
    """
    id: UUID
    nome_comercial: str
    cnpj_masked: str
    cep: str
    logradouro: str
    numero: str
    complemento: Optional[str]
    bairro: str
    cidade: str
    estado: str
    latitude: float
    longitude: float
    telefone: Optional[str]
    email: str
    ativo: bool
    is_deleted: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class BarbeariaListDTO(BaseModel):
    """
    DTO para listagem de barbearias (campos resumidos).
    """
    id: UUID
    nome_comercial: str
    cnpj_masked: str
    cidade: str
    estado: str
    telefone: Optional[str]
    ativo: bool
    is_deleted: bool

    class Config:
        from_attributes = True


class BarbeariaListWithDistanceDTO(BarbeariaListDTO):
    """
    DTO para listagem de barbearias com distância (busca por proximidade).
    Herda de BarbeariaListDTO e adiciona distancia_metros calculada pelo PostGIS.
    """
    distancia_metros: Optional[float] = None


# ═══════════════════════════════════════════════════════════
# DTOs DE RESULTADO (Service Results) — SEM Any!
# ═══════════════════════════════════════════════════════════

class ServiceResultSingleDTO(BaseModel):
    """
    DTO para resultado de operações que retornam UM ÚNICO objeto.
    Ex: criar_barbearia, obter_barbearia, atualizar_barbearia
    """
    success: bool
    data: Optional[BarbeariaResponseDTO] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class ServiceResultListDTO(BaseModel):
    """
    DTO para resultado de operações que retornam uma LISTA de objetos.
    Ex: listar_barbearias
    """
    success: bool
    data: Optional[List[BarbeariaListDTO]] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class ServiceResultMessageDTO(BaseModel):
    """
    DTO para resultado de operações que retornam apenas MENSAGENS.
    Ex: deletar_barbearia
    """
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


# ═══════════════════════════════════════════════════════════
# DTOs DE BUSCA (Selectors)
# ═══════════════════════════════════════════════════════════

class ProximidadeSearchDTO(BaseModel):
    """
    DTO para busca de barbearias por proximidade.
    Usa coordenadas geográficas para encontrar barbearias próximas.
    """
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    raio_km: float = Field(default=5.0, gt=0, le=100, description="Raio de busca em KM")

    class Config:
        from_attributes = True
