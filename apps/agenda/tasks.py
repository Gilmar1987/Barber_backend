# apps/agenda/tasks.py
"""
📖 MANIFESTO (Skill 05 - Tarefas Assíncronas):
"Tarefas pesadas ou de I/O (e-mail) devem ser delegadas ao Celery."
"Tasks devem receber apenas IDs, não objetos inteiros, para evitar payloads grandes."
"""
import logging
from celery import shared_task
from apps.agenda.models import Agendamento
from common.email_service import BrevoEmailService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_notificacoes_agendamento(self, agendamento_id: int):
    """
    Envia e-mails de confirmação para o Profissional e para o Cliente (se cadastrado).
    """
    try:
        # 1. Busca dados frescos com select_related para evitar N+1 queries
        agendamento = Agendamento.objects.select_related(
            'profissional__usuario',
            'servico',
            'barbearia',
            'cliente'
        ).get(id=agendamento_id)

        profissional_nome = agendamento.profissional.usuario.get_full_name() or agendamento.profissional.usuario.username
        profissional_email = agendamento.profissional.usuario.email
        barbearia_nome = agendamento.barbearia.nome_comercial
        cliente_nome = agendamento.nome_cliente
        telefone_cliente = agendamento.telefone_cliente
        servico_nome = agendamento.servico.nome
        data_fmt = agendamento.data.strftime('%d/%m/%Y')
        hora_fmt = agendamento.hora_inicio.strftime('%H:%M')

        # 2. Notificar o Profissional (se tiver e-mail cadastrado)
        if profissional_email:
            BrevoEmailService.enviar_confirmacao_agendamento_profissional(
                nome_profissional=profissional_nome,
                email_profissional=profissional_email,
                nome_cliente=cliente_nome,
                telefone_cliente=telefone_cliente,
                servico=servico_nome,
                data=data_fmt,
                hora=hora_fmt,
                nome_barbearia=barbearia_nome
            )

        # 3. Notificar o Cliente (apenas se for usuário cadastrado com e-mail)
        if agendamento.cliente and agendamento.cliente.email:
            BrevoEmailService.enviar_confirmacao_agendamento_cliente(
                nome_cliente=cliente_nome,
                email_cliente=agendamento.cliente.email,
                servico=servico_nome,
                data=data_fmt,
                hora=hora_fmt,
                nome_barbearia=barbearia_nome,
                nome_profissional=profissional_nome
            )

        logger.info(f"✅ Notificações do agendamento {agendamento_id} processadas com sucesso.")
        return True

    except Agendamento.DoesNotExist:
        logger.error(f"❌ Agendamento {agendamento_id} não encontrado para notificação.")
        return False  # Não retryar se o agendamento foi deletado
        
    except Exception as exc:
        logger.exception(f"⚠️ Falha ao processar notificação do agendamento {agendamento_id}")
        # Lógica de Retry do Celery em caso de falha temporária (ex: API do Brevo fora do ar)
        raise self.retry(exc=exc)