# [Domínio: core] [Skill: events]
"""
📖 MANIFESTO (Seção 5 - EDA):
"Desacoplamento por Eventos: Lógicas secundárias operam de forma assíncrona.
Handlers assíncronos gerenciados por Celery + Redis escutam esse evento."

📖 MANIFESTO (Negative Constraints):
"Toda inteligência reside no Service ou em handlers de eventos assíncronos."

✅ Regras seguidas:
- dispatch_event enfileira tarefas no Celery
- Eventos são tipados (enum)
- Payload é validado com Pydantic
- Handlers são registrados dinamicamente
- Fallback síncrono se Celery não estiver disponível
"""
import logging
from enum import Enum
from typing import Any, Callable, Dict, List
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Eventos do sistema (EDA)."""
    # Core
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # Tenants
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    
    # Agenda
    APPOINTMENT_SCHEDULED = "appointment.scheduled"
    APPOINTMENT_COMPLETED = "appointment.completed"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    
    # BI
    COMMISSION_CALCULATED = "commission.calculated"
    REVENUE_UPDATED = "revenue.updated"


class EventPayload(BaseModel):
    """Payload base para todos os eventos."""
    event_type: EventType
    tenant_id: UUID
    user_id: UUID
    data: Dict[str, Any]
    
    class Config:
        use_enum_values = True


# Registry de handlers (mapeia evento → lista de handlers)
_event_handlers: Dict[EventType, List[Callable[[EventPayload], None]]] = {}


def register_handler(event_type: EventType) -> Callable:
    """
    Decorator para registrar handlers de eventos.
    
    Uso:
        @register_handler(EventType.USER_CREATED)
        def send_welcome_email(payload: EventPayload):
            ...
    """
    def decorator(func: Callable[[EventPayload], None]) -> Callable:
        if event_type not in _event_handlers:
            _event_handlers[event_type] = []
        _event_handlers[event_type].append(func)
        return func
    return decorator


def dispatch_event(
    event_type: EventType,
    tenant_id: UUID,
    user_id: UUID,
    data: Dict[str, Any]
) -> None:
    """
    Dispara um evento assíncrono via Celery.
    Se Celery não estiver disponível, executa síncrono (fallback).
    """
    payload = EventPayload(
        event_type=event_type,
        tenant_id=tenant_id,
        user_id=user_id,
        data=data
    )
    
    try:
        # Tenta enfileirar no Celery
        from config.celery import app as celery_app
        process_event_async.delay(payload.model_dump_json())
        logger.info(f"Evento enfileirado: {event_type.value}")
    except Exception as e:
        # Fallback síncrono (desenvolvimento ou Celery indisponível)
        logger.warning(f"Celery indisponível, executando síncrono: {e}")
        _execute_handlers_sync(payload)


def _execute_handlers_sync(payload: EventPayload) -> None:
    """Executa handlers síncronamente (fallback)."""
    handlers = _event_handlers.get(EventType(payload.event_type), [])
    for handler in handlers:
        try:
            handler(payload)
        except Exception as e:
            logger.error(f"Erro no handler {handler.__name__}: {e}")


# Task Celery assíncrona
try:
    from celery import shared_task
    
    @shared_task(name="core.process_event_async")
    def process_event_async(payload_json: str) -> None:
        """Task Celery para processar eventos assíncronos."""
        payload = EventPayload.model_validate_json(payload_json)
        _execute_handlers_sync(payload)
        
except ImportError:
    # Celery não instalado (desenvolvimento)
    def process_event_async(payload_json: str) -> None:
        """Fallback síncrono quando Celery não está disponível."""
        payload = EventPayload.model_validate_json(payload_json)
        _execute_handlers_sync(payload)