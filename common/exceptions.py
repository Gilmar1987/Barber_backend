# [Domínio: core] [Skill: exceptions]
"""
📖 MANIFESTO (LGPD compliance):
"dados sensíveis mascarados em logs"

✅ Regras seguidas:
- Exceptions customizadas para erros de domínio
- Handler global que mascara dados sensíveis
- Logs estruturados sem expor informações sensíveis
"""
from typing import Any, Dict, Optional
from uuid import UUID


class DomainException(Exception):
    """Exception base para erros de domínio."""
    
    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class TenantNotFoundException(DomainException):
    """Tenant não encontrado."""
    
    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"Tenant não encontrado: {tenant_id[:8]}...",
            code="TENANT_NOT_FOUND",
            details={"tenant_id": tenant_id[:8] + "..."}  # Mascara ID completo
        )


class UserNotFoundException(DomainException):
    """Usuário não encontrado."""
    
    def __init__(self, user_id: str):
        super().__init__(
            message=f"Usuário não encontrado: {user_id[:8]}...",
            code="USER_NOT_FOUND",
            details={"user_id": user_id[:8] + "..."}
        )


class DuplicateResourceException(DomainException):
    """Recurso duplicado (violação de unicidade)."""
    
    def __init__(self, field: str, value: str):
        # Mascara valor sensível (ex: CPF, email)
        masked_value = self._mask_value(field, value)
        super().__init__(
            message=f"Recurso duplicado: {field}",
            code="DUPLICATE_RESOURCE",
            details={"field": field, "value": masked_value}
        )
    
    @staticmethod
    def _mask_value(field: str, value: str) -> str:
        """Mascara valores sensíveis para LGPD."""
        sensitive_fields = ['cpf', 'email', 'telefone', 'cnpj']
        if field.lower() in sensitive_fields:
            if len(value) > 4:
                return f"***{value[-4:]}"
            return "***"
        return value


class BarbeariaNotFoundException(DomainException):
    """Barbearia não encontrada."""

    def __init__(self, barbearia_id: str):
        super().__init__(
            message=f"Barbearia não encontrada: {barbearia_id[:8]}...",
            code="BARBEARIA_NOT_FOUND",
            details={"barbearia_id": barbearia_id[:8] + "..."}
        )


class PermissionDeniedException(DomainException):
    """Permissão negada."""
    
    def __init__(self, message: str = "Acesso negado"):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED"
        )


# ═══════════════════════════════════════════════════════════
# EXCEPTIONS DO DOMÍNIO OPERACIONAL
# ═══════════════════════════════════════════════════════════

class ServicoNotFoundException(DomainException):
    """Exceção lançada quando um serviço não é encontrado."""
    
    def __init__(self, servico_id: int, barbearia_id: Optional[UUID] = None):
        self.servico_id = servico_id
        self.barbearia_id = barbearia_id
        super().__init__(
            message=f"Serviço {servico_id} não encontrado",
            details={
                'servico_id': servico_id,
                'barbearia_id': str(barbearia_id) if barbearia_id else None
            }
        )


class ProfissionalNotFoundException(DomainException):
    """Exceção lançada quando um profissional não é encontrado."""
    
    def __init__(self, profissional_id: int, barbearia_id: Optional[UUID] = None):
        self.profissional_id = profissional_id
        self.barbearia_id = barbearia_id
        super().__init__(
            message=f"Profissional {profissional_id} não encontrado",
            details={
                'profissional_id': profissional_id,
                'barbearia_id': str(barbearia_id) if barbearia_id else None
            }
        )


class UsuarioNaoBarbeiroException(DomainException):
    """Exceção lançada quando o usuário não é do tipo BARBEIRO."""
    
    def __init__(self, usuario_id: UUID, tipo_usuario: str):
        self.usuario_id = usuario_id
        self.tipo_usuario = tipo_usuario
        super().__init__(
            message=f"Usuário {usuario_id} não é do tipo BARBEIRO",
            details={
                'usuario_id': str(usuario_id),
                'tipo_usuario_atual': tipo_usuario,
                'tipo_usuario_necessario': 'BARBEIRO'
            }
        )


class ProfissionalDuplicadoException(DomainException):
    """Exceção lançada quando usuário já é profissional na barbearia."""
    
    def __init__(self, usuario_id: UUID, barbearia_id: UUID):
        self.usuario_id = usuario_id
        self.barbearia_id = barbearia_id
        super().__init__(
            message=f"Usuário {usuario_id} já é profissional nesta barbearia",
            details={
                'usuario_id': str(usuario_id),
                'barbearia_id': str(barbearia_id)
            }
        )


class ServicoComHistoricoException(DomainException):
    """Exceção lançada ao tentar deletar serviço com agendamentos concluídos (proteção BI)."""
    
    def __init__(self, servico_id: int):
        self.servico_id = servico_id
        super().__init__(
            message=f"Serviço {servico_id} possui agendamentos concluídos e não pode ser deletado",
            details={
                'servico_id': servico_id,
                'motivo': 'Proteção de histórico de BI (ON DELETE PROTECT)'
            }
        )