# [Domínio: core] [Skill: event_handler]
"""
📖 MANIFESTO (Seção 5 - EDA):
"Handlers assíncronos gerenciados por Celery + Redis escutam esse evento
para: calcular comissão do profissional, atualizar faturamento do painel
de BI e disparar notificações push/WhatsApp."

✅ Regras seguidas:
- Handlers registrados via decorator @register_handler
- Handlers recebem EventPayload tipado
- Handlers são idempotentes (podem ser executados múltiplas vezes)
- Logs estruturados para observabilidade
"""
import logging

from common.events import EventPayload, EventType, register_handler

logger = logging.getLogger(__name__)


@register_handler(EventType.USER_CREATED)
def handle_user_created(payload: EventPayload) -> None:
    """
    Handler para evento USER_CREATED.
    Exemplos de ações:
    - Enviar email de boas-vindas
    - Criar registro de auditoria
    - Notificar administradores
    """
    logger.info(
        f"Handler USER_CREATED executado: user_id={payload.data.get('user_id')}"
    )
    # TODO: Implementar ações assíncronas
    # - send_welcome_email.delay(payload.data)
    # - notify_admins.delay(payload.data)


@register_handler(EventType.USER_UPDATED)
def handle_user_updated(payload: EventPayload) -> None:
    """Handler para evento USER_UPDATED."""
    logger.info(
        f"Handler USER_UPDATED executado: user_id={payload.data.get('user_id')}"
    )
    # TODO: Implementar ações assíncronas
    # - audit_log.delay(payload.data)


@register_handler(EventType.USER_DELETED)
def handle_user_deleted(payload: EventPayload) -> None:
    """Handler para evento USER_DELETED."""
    logger.info(
        f"Handler USER_DELETED executado: user_id={payload.data.get('user_id')}"
    )
    # TODO: Implementar ações assíncronas
    # - cleanup_related_data.delay(payload.data)