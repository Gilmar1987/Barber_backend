# [Domínio: common/email_service.py] [Skill: email]
"""
📖 MANIFESTO (Integração Externa):
"Serviços externos (email, SMS) devem ser abstraídos em camadas isoladas."

✅ Regras seguidas:
- Abstração do provedor de email (Brevo)
- Templates reutilizáveis
- Fallback para logs em ambiente de desenvolvimento
- Async-ready (pode ser chamado via Celery)
- Timeout configurável
- Tratamento robusto de erros
"""
import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """
    Service para envio de emails via Brevo (antigo Sendinblue).
    
    Documentação: https://developers.brevo.com/reference/sendtransacemail
    """
    
    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
    DEFAULT_TIMEOUT = 10  # segundos
    
    @staticmethod
    def enviar_email(
        para: str,
        nome_destinatario: str,
        assunto: str,
        html_content: str,
        de_nome: str = "BarberHub",
        de_email: Optional[str] = None,
    ) -> bool:
        """
        Envia email via Brevo API.
        
        Args:
            para: Email do destinatário
            nome_destinatario: Nome do destinatário
            assunto: Assunto do email
            html_content: Conteúdo HTML do email
            de_nome: Nome do remetente (padrão: "BarberHub")
            de_email: Email do remetente (padrão: config BREVO_SENDER_EMAIL)
        
        Returns:
            True se enviado com sucesso, False caso contrário.
        """
        api_key = getattr(settings, 'BREVO_API_KEY', None)
        sender_email = de_email or getattr(settings, 'BREVO_SENDER_EMAIL')
        
        if not api_key:
            logger.warning(
                "BREVO_API_KEY não configurada. Email não enviado.",
                extra={'para': para, 'assunto': assunto}
            )
            logger.info(
                f"[EMAIL SIMULADO] Para: {para} | Assunto: {assunto}"
            )
            return False
        
        try:
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": api_key,
            }
            
            data = {
                "sender": {"name": de_nome, "email": sender_email},
                "to": [{"email": para, "name": nome_destinatario}],
                "subject": assunto,
                "htmlContent": html_content,
            }
            
            response = requests.post(
                BrevoEmailService.BREVO_API_URL,
                json=data,
                headers=headers,
                timeout=BrevoEmailService.DEFAULT_TIMEOUT,
            )
            
            if response.status_code == 201:
                logger.info(
                    f"✅ Email enviado para {para} | Assunto: {assunto}"
                )
                return True
            else:
                logger.error(
                    f"❌ Erro ao enviar email: {response.status_code} - {response.text}",
                    extra={'para': para, 'status_code': response.status_code}
                )
                return False
        
        except requests.Timeout:
            logger.error(
                f"❌ Timeout ao enviar email para {para}",
                exc_info=True
            )
            return False
        except requests.RequestException as e:
            logger.error(
                f"❌ Erro de conexão ao enviar email: {e}",
                exc_info=True
            )
            return False
        except Exception as e:
            logger.error(
                f"❌ Exceção inesperada ao enviar email: {e}",
                exc_info=True
            )
            return False
    
    @staticmethod
    def enviar_convite_profissional(
        nome_barbeiro: str,
        email_barbeiro: str,
        nome_barbearia: str,
        comissao_percentual: int,
        token: str,
        frontend_url: Optional[str] = None,
    ) -> bool:
        """
        Envia email de convite para barbeiro.
        
        Args:
            nome_barbeiro: Nome completo do barbeiro
            email_barbeiro: Email do barbeiro
            nome_barbearia: Nome da barbearia
            comissao_percentual: Comissão oferecida
            token: Token único para aceitação
            frontend_url: URL do frontend (padrão: config FRONTEND_URL)
        
        Returns:
            True se enviado com sucesso, False caso contrário.
        """
        frontend_url = frontend_url or getattr(
            settings, 'FRONTEND_URL', 'http://localhost:3000'
        )
        link_aceite = f"{frontend_url}/convites/aceitar/{token}/"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Convite para trabalhar na {nome_barbearia}</h1>
                
                <p>Olá <strong>{nome_barbeiro}</strong>,</p>
                
                <p>Você foi convidado para trabalhar como barbeiro na 
                   <strong>{nome_barbearia}</strong>!</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Detalhes da Proposta:</h3>
                    <ul>
                        <li><strong>Barbearia:</strong> {nome_barbearia}</li>
                        <li><strong>Comissão oferecida:</strong> {comissao_percentual}%</li>
                    </ul>
                </div>
                
                <p>Para aceitar este convite e criar sua conta na plataforma, 
                   clique no botão abaixo:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{link_aceite}" 
                       style="background-color: #3498db; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Aceitar Convite
                    </a>
                </div>
                
                <p style="font-size: 12px; color: #7f8c8d;">
                    Este convite expira em 7 dias. Se você não reconhece este convite, 
                    pode ignorar este email com segurança.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">
                
                <p style="font-size: 12px; color: #95a5a6; text-align: center;">
                    BarberHub - Plataforma de Gestão para Barbearias<br>
                    Este é um email automático, por favor não responda.
                </p>
            </div>
        </body>
        </html>
        """
        
        return BrevoEmailService.enviar_email(
            para=email_barbeiro,
            nome_destinatario=nome_barbeiro,
            assunto=f"Convite para trabalhar na {nome_barbearia}",
            html_content=html_content,
        )
    
    @staticmethod
    def enviar_confirmacao_agendamento_profissional(
        nome_profissional: str,
        email_profissional: str,
        nome_cliente: str,
        telefone_cliente: str,
        servico: str,
        data: str,
        hora: str,
        nome_barbearia: str,
    ) -> bool:
        """Envia email de novo agendamento para o profissional."""
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">💈 Novo Agendamento Recebido!</h1>
                <p>Olá <strong>{nome_profissional}</strong>,</p>
                <p>Você tem um novo agendamento na <strong>{nome_barbearia}</strong>:</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <ul style="list-style: none; padding: 0;">
                        <li><strong>👤 Cliente:</strong> {nome_cliente} ({telefone_cliente})</li>
                        <li><strong>✂️ Serviço:</strong> {servico}</li>
                        <li><strong>📅 Data:</strong> {data} às {hora}</li>
                    </ul>
                </div>
                <p style="font-size: 12px; color: #7f8c8d;">Acesse o sistema BarberHub para gerenciar sua agenda.</p>
            </div>
        </body>
        </html>
        """
        return BrevoEmailService.enviar_email(
            para=email_profissional,
            nome_destinatario=nome_profissional,
            assunto=f"Novo Agendamento: {servico} em {data}",
            html_content=html_content,
        )

    @staticmethod
    def enviar_confirmacao_agendamento_cliente(
        nome_cliente: str,
        email_cliente: str,
        servico: str,
        data: str,
        hora: str,
        nome_barbearia: str,
        nome_profissional: str,
    ) -> bool:
        """Envia email de confirmação de agendamento para o cliente final."""
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">✅ Agendamento Confirmado!</h1>
                <p>Olá <strong>{nome_cliente}</strong>,</p>
                <p>Seu agendamento na <strong>{nome_barbearia}</strong> foi confirmado com sucesso:</p>
                
                <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4caf50;">
                    <ul style="list-style: none; padding: 0;">
                        <li><strong>✂️ Serviço:</strong> {servico}</li>
                        <li><strong>👤 Profissional:</strong> {nome_profissional}</li>
                        <li><strong>📅 Data:</strong> {data} às {hora}</li>
                    </ul>
                </div>
                <p style="font-size: 12px; color: #7f8c8d;">Precisa alterar ou cancelar? Acesse o sistema ou entre em contato com a barbearia.</p>
            </div>
        </body>
        </html>
        """
        return BrevoEmailService.enviar_email(
            para=email_cliente,
            nome_destinatario=nome_cliente,
            assunto=f"Confirmação de Agendamento - {nome_barbearia}",
            html_content=html_content,
        )