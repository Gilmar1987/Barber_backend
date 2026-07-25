# apps/operacional/tasks.py
"""
📖 MANIFESTO (Skill 05 - Tarefas Assíncronas):
"Tarefas pesadas ou de I/O (e-mail) devem ser delegadas ao Celery."
"Tasks devem receber apenas IDs, não objetos inteiros, para evitar payloads grandes."
"""
import logging
from celery import shared_task
from django.conf import settings
from apps.operacional.models import ConviteProfissional
from common.email_service import BrevoEmailService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_convite_profissional_task(self, convite_id: int):
    """
    Envia o email de convite para o profissional de forma assíncrona.
    """
    try:
        # 1. Busca dados frescos do banco
        convite = ConviteProfissional.objects.select_related('barbearia').get(id=convite_id)
        
        # 2. Segurança: Se o convite já foi respondido, não enviamos e-mail
        if convite.status != ConviteProfissional.STATUS_PENDENTE:
            logger.info(f"Convite {convite_id} já foi respondido. Email não enviado.")
            return True

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        
        # 3. Chama o serviço de email
        sucesso = BrevoEmailService.enviar_convite_profissional(
            nome_barbeiro=convite.nome_completo,
            email_barbeiro=convite.email,
            nome_barbearia=convite.barbearia.nome_comercial,
            comissao_percentual=convite.comissao_percentual,
            token=convite.token,
            frontend_url=frontend_url
        )
        
        if sucesso:
            logger.info(f"✅ Email de convite enviado com sucesso para {convite.email} (Convite ID: {convite_id})")
            return True
        else:
            logger.error(f"❌ Falha ao enviar email para {convite.email} (Convite ID: {convite_id})")
            raise Exception("Falha no envio do email via Brevo")

    except ConviteProfissional.DoesNotExist:
        logger.error(f"Convite ID {convite_id} não encontrado no banco. Cancelando tarefa.")
        return False
    except Exception as exc:
        logger.exception(f"⚠️ Erro inesperado ao processar tarefa de envio de convite {convite_id}")
        raise self.retry(exc=exc)