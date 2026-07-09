# [Domínio: core] [Skill: dto]
"""
📖 MANIFESTO (Negative Constraints):
"PROIBIDO vazar dicionários primitivos (request.data) para o Service sem
validação prévia por um Serializer fortemente tipado (Type Hints obrigatórios;
Any proibido)."

✅ Regras seguidas:
- Pydantic DTOs para entrada/saída de Services
- Validação forte de tipos (sem Any)
- DTOs específicos para cada caso de uso (single, list, message)
- Type safety mantida em todas as camadas
"""
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ═══════════════════════════════════════════════════════════
# DTOs de ENTRADA (Input)
# ═══════════════════════════════════════════════════════════

class UsuarioCreateDTO(BaseModel):
    """DTO para criação de usuário."""
    username: str = Field(..., min_length=3, max_length=150)
    first_name: str = Field("", max_length=150)
    last_name: str = Field("", max_length=150)
    email: EmailStr
    cpf: str = Field(..., min_length=11, max_length=11)
    password: str = Field(..., min_length=8)
    tipo_usuario: str = Field(..., pattern='^(CLIENTE_FINAL|BARBEIRO|DONO)$')
    telefone: Optional[str] = Field(None, max_length=15)
    
    @field_validator('cpf')
    @classmethod
    def validate_cpf(cls, validarCpf: str) -> str:
        if not validarCpf.isdigit():
            raise ValueError('CPF deve conter apenas números')
        return validarCpf
    
    @field_validator('telefone')
    @classmethod
    def validate_telefone(cls, validarFone: Optional[str]) -> Optional[str]:
        if validarFone is not None and not validarFone.isdigit():
            raise ValueError('Telefone deve conter apenas números')
        return validarFone


class UsuarioUpdateDTO(BaseModel):
    """DTO para atualização de usuário."""
    first_name: Optional[str] = Field(None, max_length=150)
    last_name: Optional[str] = Field(None, max_length=150)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = Field(None, max_length=15)
    password: Optional[str] = Field(None, min_length=8)
    
    @field_validator('telefone')
    @classmethod
    def validate_telefone(cls, validarFone: Optional[str]) -> Optional[str]:
        if validarFone is not None and not validarFone.isdigit():
            raise ValueError('Telefone deve conter apenas números')
        return validarFone


# ═══════════════════════════════════════════════════════════
# DTOs de SAÍDA (Output)
# ═══════════════════════════════════════════════════════════

class UsuarioResponseDTO(BaseModel):
    """DTO para resposta de usuário único (não expõe dados sensíveis)."""
    id: UUID
    username: str
    first_name: str = ""
    last_name: str = ""
    email: str
    cpf_masked: str
    tipo_usuario: str
    telefone: Optional[str]
    date_joined: str
    
    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# DTOs de RESULTADO (Service Results) - SEM Any!
# ═══════════════════════════════════════════════════════════

class ServiceResultSingleDTO(BaseModel):
    """
    DTO para resultado de operações que retornam UM ÚNICO objeto.
    Ex: criar_usuario, obter_usuario, atualizar_usuario
    """
    success: bool
    data: Optional[UsuarioResponseDTO] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class ServiceResultListDTO(BaseModel):
    """
    DTO para resultado de operações que retornam uma LISTA de objetos.
    Ex: listar_usuarios
    """
    success: bool
    data: Optional[List[UsuarioResponseDTO]] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class ServiceResultMessageDTO(BaseModel):
    """
    DTO para resultado de operações que retornam apenas MENSAGENS.
    Ex: deletar_usuario
    """
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None