# [Domínio: core] [Skill: context]
"""
📖 MANIFESTO (Seção 1 - Isolamento Multi-Tenant):
"Um middleware captura o identificador do tenant a partir do JWT e o injeta
em um armazenamento local seguro por thread (threading.local() ou contextvars)."

📖 MANIFESTO (Negative Constraints):
"Toda e qualquer query DEVE incluir explicitamente o contexto do inquilino
(tenant_id ou escopo de thread local do locatário)."

✅ Regras seguidas:
- Usa contextvars (thread-safe + async-safe) em vez de threading.local
- Fornece funções get/set para o tenant_id
- Fornece funções get/set para o user_id (auditoria)
"""
from contextvars import ContextVar
from typing import Optional
from uuid import UUID

# ContextVar é thread-safe E async-safe (melhor que threading.local)
_current_tenant_id: ContextVar[Optional[UUID]] = ContextVar(
    'current_tenant_id',
    default=None
)

_current_user_id: ContextVar[Optional[UUID]] = ContextVar(
    'current_user_id',
    default=None
)


def set_current_tenant_id(tenant_id: Optional[UUID]) -> None:
    """Define o tenant_id da requisição atual no contexto."""
    _current_tenant_id.set(tenant_id)


def get_current_tenant_id() -> Optional[UUID]:
    """Retorna o tenant_id da requisição atual."""
    return _current_tenant_id.get()


def set_current_user_id(user_id: Optional[UUID]) -> None:
    """Define o user_id da requisição atual (para auditoria)."""
    _current_user_id.set(user_id)


def get_current_user_id() -> Optional[UUID]:
    """Retorna o user_id da requisição atual."""
    return _current_user_id.get()


def clear_context() -> None:
    """Limpa o contexto (útil em testes e após requisições)."""
    _current_tenant_id.set(None)
    _current_user_id.set(None)