# [Domínio: operacional] [Skill: service]
"""
📖 MANIFESTO (Skill 03 - Service):
"Toda a inteligência reside no Service ou em handlers de eventos assíncronos."

📖 MANIFESTO (Negative Constraints):
"PROIBIDO acessar `request` em Services, Selectors ou Repositories"
"PROIBIDO vazar dicionários primitivos (request.data) para o Service"

✅ Regras seguidas:
- Services recebem DTOs Pydantic (não Dict)
- Services retornam DTOs específicos (sem Any)
- Services NÃO acessam request HTTP
- Services delegam persistência ao Repository
- Services validam regras de negócio
- dispatch_event isolado em try/except próprio
- logging.exception() para erros inesperados (CWE-396/703)
"""
import logging
from datetime import datetime
from django.conf import settings
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from django.db import DatabaseError, OperationalError

from apps.operacional.dtos import (
    DiaIndisponivelCreateDTO,
    DiaIndisponivelResponseDTO,
    GradeHorariaCreateDTO,
    GradeHorariaResponseDTO,
    GradeHorariaUpdateDTO,
    IntervaloIndisponivelCreateDTO,
    IntervaloIndisponivelResponseDTO,
    ProfissionalCreateDTO,
    ProfissionalResponseDTO,
    ProfissionalUpdateDTO,
    ServicoCreateDTO,
    ServicoHabilitadoResponseDTO,
    ServicoResponseDTO,
    ServicoUpdateDTO,
    ServiceResultListDTO,
    ServiceResultMessageDTO,
    ServiceResultSingleDTO,
    ConviteProfissionalCreateDTO,
    ConviteProfissionalResponseDTO,
    ConviteAceiteResponseDTO,
)
from apps.operacional.repository import (
    ConviteProfissionalRepository,
    DiaIndisponivelRepository,
    GradeHorariaRepository,
    IntervaloIndisponivelRepository,
    ProfissionalRepository,
    ServicoProfissionalRepository,
    ServicoRepository,
)
from common.events import EventType, dispatch_event
from apps.operacional.models import ConviteProfissional
from common.exceptions import (
    ConviteNotFoundException,
    DiaIndisponivelConflictException,
    DiaIndisponivelNotFoundException,
    DomainException,
    GradeHorariaConflictException,
    GradeHorariaNotFoundException,
    IntervaloIndisponivelConflictException,
    IntervaloIndisponivelNotFoundException,
    ProfissionalNotFoundException,
    ServicoNotFoundException,
    ServicoComHistoricoException,
    UsuarioNaoBarbeiroException,
    ServicoProfissionalConflictException,
    ProfissionalDuplicadoException,
    ConviteExpiradoException,
    ConviteDuplicadoException,
    ProfissionalJaVinculadoException,
    ConviteJaRespondidoException,
    
    

)

logger = logging.getLogger(__name__)


class ServicoService:
    """Service para operações com Serviços de uma barbearia."""

    def __init__(self, repository: Optional[ServicoRepository] = None):
        self.repository = repository or ServicoRepository()

    def criar_servico(
        self,
        dto: ServicoCreateDTO,
        barbearia_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """Cria novo serviço vinculado à barbearia."""
        try:
            servico = self.repository.create(dto, barbearia_id=barbearia_id, created_by=user_id)
            logger.info('Serviço criado: %s | barbearia: %s', servico.id, barbearia_id)
            response_dto = self._to_response_dto(servico)
            result = ServiceResultSingleDTO(success=True, data=response_dto)

            try:
                dispatch_event(
                    event_type=EventType.TENANT_UPDATED,
                    tenant_id=barbearia_id,
                    user_id=user_id or barbearia_id,
                    data={'servico_id': servico.id, 'action': 'servico_criado'},
                )
            except Exception:
                logging.exception('Falha ao disparar evento servico_criado')

            return result

        except DomainException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao criar serviço')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao criar serviço')
        except Exception:
            logging.exception('Erro inesperado ao criar serviço')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao criar serviço')

    def obter_servico(self, servico_id: int, barbearia_id: UUID) -> ServiceResultSingleDTO:
        """Retorna dados de um serviço específico."""
        try:
            servico = self.repository.get_by_id_or_raise(servico_id, barbearia_id)
            return ServiceResultSingleDTO(success=True, data=self._to_response_dto(servico))
        except ServicoNotFoundException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao obter serviço')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao obter serviço')
        except Exception:
            logging.exception('Erro inesperado ao obter serviço')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao obter serviço')

    def listar_servicos(
        self, barbearia_id: UUID, ativo_only: bool = True
    ) -> ServiceResultListDTO:
        """Lista serviços da barbearia."""
        try:
            servicos = self.repository.get_all_by_barbearia(barbearia_id, ativo_only=ativo_only)
            return ServiceResultListDTO(
                success=True,
                data=[self._to_response_dto(s) for s in servicos],
            )
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao listar serviços')
            return ServiceResultListDTO(success=False, error='Erro interno ao listar serviços')
        except Exception:
            logging.exception('Erro inesperado ao listar serviços')
            return ServiceResultListDTO(success=False, error='Erro interno ao listar serviços')

    def atualizar_servico(
        self,
        servico_id: int,
        barbearia_id: UUID,
        dto: ServicoUpdateDTO,
        updated_by: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """Atualiza serviço existente."""
        try:
            servico = self.repository.get_by_id_or_raise(servico_id, barbearia_id)
            updated = self.repository.update(servico, dto, updated_by=updated_by)
            logger.info('Serviço atualizado: %s', servico_id)
            return ServiceResultSingleDTO(success=True, data=self._to_response_dto(updated))
        except ServicoNotFoundException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except DomainException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao atualizar serviço')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao atualizar serviço')
        except Exception:
            logging.exception('Erro inesperado ao atualizar serviço')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao atualizar serviço')

    def deletar_servico(
        self, servico_id: int, barbearia_id: UUID, deleted_by: Optional[UUID] = None
    ) -> ServiceResultMessageDTO:
        """
        Desativa serviço (toggle ativo=False).
        Hard delete bloqueado se houver agendamentos concluídos (proteção BI).
        """
        try:
            servico = self.repository.get_by_id_or_raise(servico_id, barbearia_id)

            if self.repository.has_agendamentos_concluidos(servico_id):
                raise ServicoComHistoricoException(servico_id)

            self.repository.toggle_ativo(servico)
            logger.info('Serviço desativado: %s', servico_id)
            return ServiceResultMessageDTO(success=True, message='Serviço desativado com sucesso')

        except (ServicoNotFoundException, ServicoComHistoricoException) as e:
            return ServiceResultMessageDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao deletar serviço')
            return ServiceResultMessageDTO(success=False, error='Erro interno ao deletar serviço')
        except Exception:
            logging.exception('Erro inesperado ao deletar serviço')
            return ServiceResultMessageDTO(success=False, error='Erro interno ao deletar serviço')

    def toggle_ativo_servico(
        self, servico_id: int, barbearia_id: UUID, user_id: Optional[UUID] = None
    ) -> ServiceResultSingleDTO:
        """Alterna status ativo/inativo do serviço."""
        try:
            servico = self.repository.get_by_id_or_raise(servico_id, barbearia_id)
            updated = self.repository.toggle_ativo(servico)
            logger.info('Toggle ativo serviço: %s → %s', servico_id, updated.ativo)
            return ServiceResultSingleDTO(success=True, data=self._to_response_dto(updated))
        except ServicoNotFoundException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao toggle serviço')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao alternar status do serviço')
        except Exception:
            logging.exception('Erro inesperado ao toggle serviço')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao alternar status do serviço')

    @staticmethod
    def _to_response_dto(servico) -> ServicoResponseDTO:
        return ServicoResponseDTO(
            id=servico.id,
            barbearia_id=servico.barbearia_id,
            nome=servico.nome,
            preco=servico.preco,
            duracao_minutos=servico.duracao_minutos,
            ativo=servico.ativo,
        )


class ProfissionalService:
    """Service para operações com Profissionais de uma barbearia."""

    def __init__(self, repository: Optional[ProfissionalRepository] = None):
        self.repository = repository or ProfissionalRepository()

    def criar_profissional(
        self,
        dto: ProfissionalCreateDTO,
        barbearia_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """Cria vínculo profissional (usuário BARBEIRO ↔ barbearia)."""
        try:
            profissional = self.repository.create(dto, barbearia_id=barbearia_id, created_by=user_id)
            logger.info(
                'Profissional criado: %s | barbearia: %s', profissional.id, barbearia_id
            )
            response_dto = self._to_response_dto(profissional)
            result = ServiceResultSingleDTO(success=True, data=response_dto)

            try:
                dispatch_event(
                    event_type=EventType.TENANT_UPDATED,
                    tenant_id=barbearia_id,
                    user_id=user_id or barbearia_id,
                    data={'profissional_id': profissional.id, 'action': 'profissional_criado'},
                )
            except Exception:
                logging.exception('Falha ao disparar evento profissional_criado')

            return result

        except (UsuarioNaoBarbeiroException, ProfissionalDuplicadoException) as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except DomainException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao criar profissional')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao criar profissional')
        except Exception:
            logging.exception('Erro inesperado ao criar profissional')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao criar profissional')

    def obter_profissional(
        self, profissional_id: int, barbearia_id: UUID
    ) -> ServiceResultSingleDTO:
        """Retorna dados de um profissional específico."""
        try:
            profissional = self.repository.get_by_id_or_raise(profissional_id, barbearia_id)
            return ServiceResultSingleDTO(success=True, data=self._to_response_dto(profissional))
        except ProfissionalNotFoundException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao obter profissional')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao obter profissional')
        except Exception:
            logging.exception('Erro inesperado ao obter profissional')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao obter profissional')

    def listar_profissionais(
        self, barbearia_id: UUID, ativo_only: bool = True
    ) -> ServiceResultListDTO:
        """Lista profissionais da barbearia."""
        try:
            profissionais = self.repository.get_all_by_barbearia(
                barbearia_id, ativo_only=ativo_only
            )
            return ServiceResultListDTO(
                success=True,
                data=[self._to_response_dto(p) for p in profissionais],
            )
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao listar profissionais')
            return ServiceResultListDTO(success=False, error='Erro interno ao listar profissionais')
        except Exception:
            logging.exception('Erro inesperado ao listar profissionais')
            return ServiceResultListDTO(success=False, error='Erro interno ao listar profissionais')

    def atualizar_profissional(
        self,
        profissional_id: int,
        barbearia_id: UUID,
        dto: ProfissionalUpdateDTO,
        updated_by: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """Atualiza comissão ou status ativo do profissional."""
        try:
            profissional = self.repository.get_by_id_or_raise(profissional_id, barbearia_id)
            updated = self.repository.update(profissional, dto, updated_by=updated_by)
            logger.info('Profissional atualizado: %s', profissional_id)
            return ServiceResultSingleDTO(success=True, data=self._to_response_dto(updated))
        except ProfissionalNotFoundException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except DomainException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao atualizar profissional')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao atualizar profissional')
        except Exception:
            logging.exception('Erro inesperado ao atualizar profissional')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao atualizar profissional')

    def toggle_ativo_profissional(
        self, profissional_id: int, barbearia_id: UUID, user_id: Optional[UUID] = None
    ) -> ServiceResultSingleDTO:
        """Alterna status ativo/inativo do profissional."""
        try:
            profissional = self.repository.get_by_id_or_raise(profissional_id, barbearia_id)
            updated = self.repository.toggle_ativo(profissional)
            logger.info('Toggle ativo profissional: %s → %s', profissional_id, updated.ativo)
            return ServiceResultSingleDTO(success=True, data=self._to_response_dto(updated))
        except ProfissionalNotFoundException as e:
            return ServiceResultSingleDTO(success=False, error=e.message, details=e.details)
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao toggle profissional')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao alternar status do profissional')
        except Exception:
            logging.exception('Erro inesperado ao toggle profissional')
            return ServiceResultSingleDTO(success=False, error='Erro interno ao alternar status do profissional')

    @staticmethod
    def _to_response_dto(profissional) -> ProfissionalResponseDTO:
        usuario = profissional.usuario
        return ProfissionalResponseDTO(
            id=profissional.id,
            barbearia_id=profissional.barbearia_id,
            usuario_id=usuario.id,
            usuario_nome=usuario.get_full_name() or usuario.username,
            comissao_percentual=profissional.comissao_percentual,
            ativo=profissional.ativo,
        )


# ═══════════════════════════════════════════════════════════
# SERVICE DE CONVITE PROFISSIONAL (FLUXO HÍBRIDO)
# ═══════════════════════════════════════════════════════════

class ConviteProfissionalService:
    """
    Service para fluxo híbrido de convite profissional.
    Implementa a lógica inteligente de criação de usuário + envio de convite.
    """
    
    def __init__(
        self,
        convite_repository: Optional[ConviteProfissionalRepository] = None,
        profissional_repository: Optional[ProfissionalRepository] = None
    ):
        self.convite_repository = convite_repository or ConviteProfissionalRepository()
        self.profissional_repository = profissional_repository or ProfissionalRepository()
    
    def criar_convite(
        self,
        dto: ConviteProfissionalCreateDTO,
        barbearia_id: UUID,
        user_id: Optional[UUID] = None
    ) -> ServiceResultSingleDTO:
        """
        Cria convite profissional com lógica híbrida.
        
        Fluxo:
        1. Busca usuário por email OU CPF
        2. Se encontrou:
           - É BARBEIRO? → Cria convite pendente + envia email
           - É CLIENTE_FINAL? → Retorna erro
           - É DONO? → Retorna erro
        3. Se NÃO encontrou:
           - Cria core_usuario (tipo=BARBEIRO)
           - Cria convite pendente
           - Envia email de boas-vindas
        """
        try:
            from apps.core.repository import UsuarioRepository
            from apps.core.models import Usuario
            from common.email_service import BrevoEmailService
            from apps.tenants.models import Barbearia
            
            # 1. Verifica se já existe convite pendente para este email nesta barbearia
            if self.convite_repository.exists_by_email_na_barbearia(dto.email, barbearia_id):
                return ServiceResultSingleDTO(
                    success=False,
                    error="Já existe um convite pendente para este email nesta barbearia.",
                    details={'email': dto.email}
                )
            
            # 2. Busca usuário por email OU CPF
            usuario = None
            usuario_existente = False
            
            try:
                # Tenta buscar por email primeiro
                usuario = Usuario.objects.get(email__iexact=dto.email)
                usuario_existente = True
            except Usuario.DoesNotExist:
                # Tenta buscar por CPF
                try:
                    usuario = Usuario.objects.get(cpf=dto.cpf)
                    usuario_existente = True
                except Usuario.DoesNotExist:
                    # Usuário não existe, será criado
                    pass
            
            # 3. Se usuário existe, valida o tipo
            if usuario_existente:
                if usuario.tipo_usuario != 'BARBEIRO':
                    tipo_mensagem = {
                        'CLIENTE_FINAL': 'Este email/CPF pertence a um cliente final. Peça para o barbeiro criar uma conta de barbeiro primeiro.',
                        'DONO': 'Este email/CPF pertence a um dono de barbearia. Não é possível vincular como profissional.'
                    }
                    return ServiceResultSingleDTO(
                        success=False,
                        error=tipo_mensagem.get(usuario.tipo_usuario, 'Tipo de usuário inválido.'),
                        details={'tipo_usuario': usuario.tipo_usuario}
                    )
                
                # Verifica se já é profissional nesta barbearia
                if self.profissional_repository.exists_by_usuario_na_barbearia(usuario.id, barbearia_id):
                    return ServiceResultSingleDTO(
                        success=False,
                        error="Este barbeiro já está vinculado a esta barbearia.",
                        details={'usuario_id': str(usuario.id)}
                    )
            
            # 4. Se usuário não existe, cria novo
            if not usuario_existente:
                # Gera username único baseado no email
                username_base = dto.email.split('@')[0].lower().replace('.', '_')
                username = username_base
                counter = 1
                while Usuario.objects.filter(username=username).exists():
                    username = f"{username_base}_{counter}"
                    counter += 1
                
                # Gera senha temporária aleatória
                import secrets
                senha_temporaria = secrets.token_urlsafe(12)
                
                usuario = Usuario.objects.create_user(
                    username=username,
                    email=dto.email,
                    password=senha_temporaria,
                    cpf=dto.cpf,
                    tipo_usuario='BARBEIRO',
                    telefone=dto.telefone,
                    first_name=dto.nome_completo.split()[0] if dto.nome_completo else '',
                    last_name=' '.join(dto.nome_completo.split()[1:]) if len(dto.nome_completo.split()) > 1 else ''
                )
            
            # 5. Cria convite pendente
            convite = self.convite_repository.create(
                dto=dto,
                barbearia_id=barbearia_id,
                usuario_id=usuario.id,
                criado_por=user_id
            )
            
            # 6. Envia email via Brevo
            barbearia = Barbearia.objects.get(id=barbearia_id)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            
            email_enviado = BrevoEmailService.enviar_convite_profissional(
                nome_barbeiro=dto.nome_completo,
                email_barbeiro=dto.email,
                nome_barbearia=barbearia.nome_comercial,
                comissao_percentual=dto.comissao_percentual,
                token=convite.token,
                frontend_url=frontend_url
            )
            
            # 7. Monta mensagem de resposta
            if usuario_existente:
                mensagem = f"Convite enviado para {dto.email}. O barbeiro já possui conta e receberá uma notificação para aceitar o vínculo."
            else:
                mensagem = f"Conta criada para {dto.email} e convite enviado. O barbeiro receberá um email com instruções para criar sua senha e aceitar o vínculo."
            
            logger.info(f"Convite criado: {convite.id} | Barbeiro: {dto.email} | Barbearia: {barbearia.nome_comercial}")
            
            response_dto = self._to_convite_response_dto(convite)
            
            return ServiceResultSingleDTO(
                success=True,
                data=response_dto,
                message=mensagem
            )
        
        except DomainException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.error(f"Erro ao criar convite: {e}", exc_info=True)
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar convite"
            )
    
    def aceitar_convite(self, token: str) -> ServiceResultSingleDTO:
        """
        Aceita convite e cria vínculo profissional.
        """
        try:
            # 1. Busca convite por token
            convite = self.convite_repository.get_by_token_or_raise(token)
            
            # 2. Valida se o convite é válido
            if not convite.is_valido():
                if convite.status == ConviteProfissional.STATUS_ACEITO:
                    return ServiceResultSingleDTO(
                        success=False,
                        error="Este convite já foi aceito."
                    )
                elif convite.status == ConviteProfissional.STATUS_RECUSADO:
                    return ServiceResultSingleDTO(
                        success=False,
                        error="Este convite foi recusado."
                    )
                else:
                    return ServiceResultSingleDTO(
                        success=False,
                        error="Este convite expirou. Solicite um novo convite."
                    )
            
            # 3. Verifica se já é profissional nesta barbearia
            if self.profissional_repository.exists_by_usuario_na_barbearia(convite.usuario_id, convite.barbearia_id):
                convite.aceitar()  # Marca como aceito mesmo assim
                return ServiceResultSingleDTO(
                    success=True,
                    message="Você já está vinculado a esta barbearia.",
                    data=ConviteAceiteResponseDTO(
                        success=True,
                        message="Vínculo já existente",
                        profissional_id=None,
                        barbearia_id=convite.barbearia_id
                    )
                )
            
            # 4. Cria vínculo profissional
            profissional_dto = ProfissionalCreateDTO(
                usuario_id=convite.usuario_id,
                comissao_percentual=convite.comissao_percentual,
                ativo=True
            )
            
            profissional = self.profissional_repository.create(
                dto=profissional_dto,
                barbearia_id=convite.barbearia_id
            )
            
            # 5. Marca convite como aceito
            convite.aceitar()
            
            logger.info(f"Convite aceito: {convite.id} | Profissional: {profissional.id}")
            
            return ServiceResultSingleDTO(
                success=True,
                message="Convite aceito com sucesso! Você agora é profissional desta barbearia.",
                data=ConviteAceiteResponseDTO(
                    success=True,
                    message="Convite aceito",
                    profissional_id=profissional.id,
                    barbearia_id=convite.barbearia_id
                )
            )
        
        except ConviteNotFoundException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except DomainException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.error(f"Erro ao aceitar convite: {e}", exc_info=True)
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao aceitar convite"
            )
    
    def _to_convite_response_dto(self, convite: ConviteProfissional) -> ConviteProfissionalResponseDTO:
        """Converte model ConviteProfissional para DTO."""
        return ConviteProfissionalResponseDTO(
            id=convite.id,
            barbearia_id=convite.barbearia_id,
            usuario_id=convite.usuario_id,
            nome_completo=convite.nome_completo,
            email=convite.email,
            cpf=convite.cpf,
            telefone=convite.telefone,
            comissao_percentual=convite.comissao_percentual,
            status=convite.status,
            data_criacao=convite.data_criacao,
            data_expiracao=convite.data_expiracao
        )
    
# ═══════════════════════════════════════════════════════════
# SERVICE DE GRADE HORÁRIA
# ═══════════════════════════════════════════════════════════

class GradeHorariaService:
    """
    Service para operações com Grade Horária.
    """
    
    DIAS_SEMANA_NOMES = {
        0: 'Domingo',
        1: 'Segunda-feira',
        2: 'Terça-feira',
        3: 'Quarta-feira',
        4: 'Quinta-feira',
        5: 'Sexta-feira',
        6: 'Sábado',
    }
    
    def __init__(self, repository: Optional[GradeHorariaRepository] = None):
        self.repository = repository or GradeHorariaRepository()
    
    def criar_grade(
        self,
        dto: GradeHorariaCreateDTO,
        profissional_id: int,
        barbearia_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """Cria nova grade horária para um profissional."""
        try:
            # Valida se o profissional pertence à barbearia (multi-tenancy)
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            profissional = profissional_repo.get_by_id(profissional_id, barbearia_id)
            if not profissional:
                return ServiceResultSingleDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia",
                    details={'profissional_id': profissional_id}
                )
            
            grade = self.repository.create(dto, profissional_id, criado_por=user_id)
            
            logger.info(
                f"Grade horária criada: {grade.id} | "
                f"Profissional: {profissional_id} | Dia: {grade.dia_semana}"
            )
            
            response_dto = self._to_response_dto(grade)
            return ServiceResultSingleDTO(success=True, data=response_dto)
        
        except GradeHorariaConflictException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao criar grade horária: {e}")
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar grade horária"
            )
    
    def listar_grades(
        self,
        profissional_id: int,
        barbearia_id: UUID,
        ativo_only: bool = True,
    ) -> ServiceResultListDTO:
        """Lista todas as grades de um profissional."""
        try:
            # Valida multi-tenancy
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            if not profissional_repo.get_by_id(profissional_id, barbearia_id):
                return ServiceResultListDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia"
                )
            
            grades = self.repository.get_all_by_profissional(profissional_id, ativo_only)
            response_dtos = [self._to_response_dto(g) for g in grades]
            
            return ServiceResultListDTO(success=True, data=response_dtos)
        
        except Exception as e:
            logger.exception(f"Erro ao listar grades: {e}")
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao listar grades"
            )
    
    def atualizar_grade(
        self,
        grade_id: int,
        dto: GradeHorariaUpdateDTO,
        profissional_id: int,
        barbearia_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """Atualiza grade existente."""
        try:
            # Valida multi-tenancy
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            if not profissional_repo.get_by_id(profissional_id, barbearia_id):
                return ServiceResultSingleDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia"
                )
            
            grade = self.repository.get_by_id_or_raise(grade_id, profissional_id)
            updated_grade = self.repository.update(grade, dto, atualizado_por=user_id)
            
            logger.info(f"Grade atualizada: {updated_grade.id}")
            
            response_dto = self._to_response_dto(updated_grade)
            return ServiceResultSingleDTO(success=True, data=response_dto)
        
        except GradeHorariaNotFoundException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao atualizar grade: {e}")
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao atualizar grade"
            )
    
    def _to_response_dto(self, grade) -> GradeHorariaResponseDTO:
        """Converte model GradeHoraria para DTO."""
        return GradeHorariaResponseDTO(
            id=grade.id,
            profissional_id=grade.profissional_id,
            dia_semana=grade.dia_semana,
            dia_semana_nome=self.DIAS_SEMANA_NOMES.get(grade.dia_semana, 'Desconhecido'),
            hora_inicio=grade.hora_inicio,
            hora_fim=grade.hora_fim,
            intervalo_inicio=grade.intervalo_inicio,
            intervalo_fim=grade.intervalo_fim,
            ativo=grade.ativo,
        )


# ═══════════════════════════════════════════════════════════
# SERVICE DE DIA INDISPONÍVEL
# ═══════════════════════════════════════════════════════════

class DiaIndisponivelService:
    """
    Service para operações com Dias Indisponíveis.
    """
    
    def __init__(self, repository: Optional[DiaIndisponivelRepository] = None):
        self.repository = repository or DiaIndisponivelRepository()
    
    def criar_dia_indisponivel(
        self,
        dto: DiaIndisponivelCreateDTO,
        profissional_id: int,
        barbearia_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """Cria novo dia indisponível."""
        try:
            # Valida multi-tenancy
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            if not profissional_repo.get_by_id(profissional_id, barbearia_id):
                return ServiceResultSingleDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia"
                )
            
            dia = self.repository.create(dto, profissional_id, criado_por=user_id)
            
            logger.info(
                f"Dia indisponível criado: {dia.id} | "
                f"Profissional: {profissional_id} | Data: {dia.data}"
            )
            
            response_dto = DiaIndisponivelResponseDTO.model_validate(dia)
            return ServiceResultSingleDTO(success=True, data=response_dto)
        
        except DiaIndisponivelConflictException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao criar dia indisponível: {e}")
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar dia indisponível"
            )
    
    def listar_dias_indisponiveis(
        self,
        profissional_id: int,
        barbearia_id: UUID,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> ServiceResultListDTO:
        """Lista dias indisponíveis de um profissional."""
        try:
            # Valida multi-tenancy
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            if not profissional_repo.get_by_id(profissional_id, barbearia_id):
                return ServiceResultListDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia"
                )
            
            dias = self.repository.get_all_by_profissional(
                profissional_id, data_inicio, data_fim
            )
            response_dtos = [DiaIndisponivelResponseDTO.model_validate(d) for d in dias]
            
            return ServiceResultListDTO(success=True, data=response_dtos)
        
        except Exception as e:
            logger.exception(f"Erro ao listar dias indisponíveis: {e}")
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao listar dias indisponíveis"
            )
    
    def deletar_dia_indisponivel(
        self,
        dia_id: int,
        profissional_id: int,
        barbearia_id: UUID,
    ) -> ServiceResultMessageDTO:
        """Deleta dia indisponível."""
        try:
            # Valida multi-tenancy
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            if not profissional_repo.get_by_id(profissional_id, barbearia_id):
                return ServiceResultMessageDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia"
                )
            
            dia = self.repository.get_by_id_or_raise(dia_id, profissional_id)
            self.repository.delete(dia)
            
            logger.info(f"Dia indisponível deletado: {dia_id}")
            
            return ServiceResultMessageDTO(
                success=True,
                message="Dia indisponível removido com sucesso"
            )
        
        except DiaIndisponivelNotFoundException as e:
            return ServiceResultMessageDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao deletar dia indisponível: {e}")
            return ServiceResultMessageDTO(
                success=False,
                error="Erro interno ao deletar dia indisponível"
            )


# ═══════════════════════════════════════════════════════════
# SERVICE DE INTERVALO INDISPONÍVEL
# ═══════════════════════════════════════════════════════════

class IntervaloIndisponivelService:
    """
    Service para operações com Intervalos Indisponíveis.
    """
    
    def __init__(self, repository: Optional[IntervaloIndisponivelRepository] = None):
        self.repository = repository or IntervaloIndisponivelRepository()
    
    def criar_intervalo_indisponivel(
        self,
        dto: IntervaloIndisponivelCreateDTO,
        profissional_id: int,
        barbearia_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """Cria novo intervalo indisponível."""
        try:
            # Valida multi-tenancy
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            if not profissional_repo.get_by_id(profissional_id, barbearia_id):
                return ServiceResultSingleDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia"
                )
            
            intervalo = self.repository.create(dto, profissional_id, criado_por=user_id)
            
            logger.info(
                f"Intervalo indisponível criado: {intervalo.id} | "
                f"Profissional: {profissional_id} | {intervalo.data} "
                f"{intervalo.hora_inicio}-{intervalo.hora_fim}"
            )
            
            response_dto = IntervaloIndisponivelResponseDTO.model_validate(intervalo)
            return ServiceResultSingleDTO(success=True, data=response_dto)
        
        except IntervaloIndisponivelConflictException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao criar intervalo indisponível: {e}")
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar intervalo indisponível"
            )
    
    def listar_intervalos_indisponiveis(
        self,
        profissional_id: int,
        barbearia_id: UUID,
        data: date,
    ) -> ServiceResultListDTO:
        """Lista intervalos indisponíveis de um profissional em uma data."""
        try:
            # Valida multi-tenancy
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            if not profissional_repo.get_by_id(profissional_id, barbearia_id):
                return ServiceResultListDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia"
                )
            
            intervalos = self.repository.get_all_by_profissional_and_data(
                profissional_id, data
            )
            response_dtos = [
                IntervaloIndisponivelResponseDTO.model_validate(i) for i in intervalos
            ]
            
            return ServiceResultListDTO(success=True, data=response_dtos)
        
        except Exception as e:
            logger.exception(f"Erro ao listar intervalos indisponíveis: {e}")
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao listar intervalos indisponíveis"
            )
    
    def deletar_intervalo_indisponivel(
        self,
        intervalo_id: int,
        profissional_id: int,
        barbearia_id: UUID,
    ) -> ServiceResultMessageDTO:
        """Deleta intervalo indisponível."""
        try:
            # Valida multi-tenancy
            from apps.operacional.repository import ProfissionalRepository
            profissional_repo = ProfissionalRepository()
            if not profissional_repo.get_by_id(profissional_id, barbearia_id):
                return ServiceResultMessageDTO(
                    success=False,
                    error="Profissional não encontrado nesta barbearia"
                )
            
            intervalo = self.repository.get_by_id_or_raise(intervalo_id, profissional_id)
            self.repository.delete(intervalo)
            
            logger.info(f"Intervalo indisponível deletado: {intervalo_id}")
            
            return ServiceResultMessageDTO(
                success=True,
                message="Intervalo indisponível removido com sucesso"
            )
        
        except IntervaloIndisponivelNotFoundException as e:
            return ServiceResultMessageDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao deletar intervalo indisponível: {e}")
            return ServiceResultMessageDTO(
                success=False,
                error="Erro interno ao deletar intervalo indisponível"
            )


# ═══════════════════════════════════════════════════════════
# SERVICE DE CONVITE PROFISSIONAL (FLUXO HÍBRIDO)
# ═══════════════════════════════════════════════════════════

class ConviteProfissionalService:
    """
    Service para fluxo híbrido de convite profissional.
    Implementa a lógica inteligente de criação de usuário + envio de convite.
    
    Fluxo:
    1. Busca usuário por email OU CPF
    2. Se encontrou:
       - É BARBEIRO? → Cria convite pendente + envia email
       - É CLIENTE_FINAL? → Retorna erro
       - É DONO? → Retorna erro
    3. Se NÃO encontrou:
       - Cria core_usuario (tipo=BARBEIRO)
       - Cria convite pendente
       - Envia email de boas-vindas
    """
    
    def __init__(
        self,
        convite_repository: Optional[ConviteProfissionalRepository] = None,
        profissional_repository: Optional[ProfissionalRepository] = None,
    ):
        self.convite_repository = convite_repository or ConviteProfissionalRepository()
        self.profissional_repository = profissional_repository or ProfissionalRepository()
    
    def criar_convite(
        self,
        dto: ConviteProfissionalCreateDTO,
        barbearia_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> ServiceResultSingleDTO:
        """
        Cria convite profissional com lógica híbrida.
        
        Retorna:
            ServiceResultSingleDTO com:
            - success=True + convite criado + email enviado
            - success=False + mensagem de erro específica
        """
        try:
            from apps.core.models import Usuario
            from apps.core.repository import UsuarioRepository
            from apps.tenants.models import Barbearia
            from common.email_service import BrevoEmailService
            
            # 1. Verifica se já existe convite pendente para este email nesta barbearia
            if self.convite_repository.exists_by_email_na_barbearia(dto.email, barbearia_id):
                raise ConviteDuplicadoException(dto.email, barbearia_id)
            
            # 2. Busca usuário por email OU CPF
            usuario = None
            usuario_existente = False
            
            try:
                # Tenta buscar por email primeiro
                usuario = Usuario.objects.get(email__iexact=dto.email)
                usuario_existente = True
            except Usuario.DoesNotExist:
                # Tenta buscar por CPF
                try:
                    usuario = Usuario.objects.get(cpf=dto.cpf)
                    usuario_existente = True
                except Usuario.DoesNotExist:
                    # Usuário não existe, será criado
                    pass
            
            # 3. Se usuário existe, valida o tipo
            if usuario_existente:
                if usuario.tipo_usuario != 'BARBEIRO':
                    tipo_mensagem = {
                        'CLIENTE_FINAL': 'Este email/CPF pertence a um cliente final. Peça para o barbeiro criar uma conta de barbeiro primeiro.',
                        'DONO': 'Este email/CPF pertence a um dono de barbearia. Não é possível vincular como profissional.'
                    }
                    return ServiceResultSingleDTO(
                        success=False,
                        error=tipo_mensagem.get(usuario.tipo_usuario, 'Tipo de usuário inválido.'),
                        details={'tipo_usuario': usuario.tipo_usuario}
                    )
                
                # Verifica se já é profissional nesta barbearia
                if self.profissional_repository.exists_by_usuario_na_barbearia(usuario.id, barbearia_id):
                    raise ProfissionalJaVinculadoException(usuario.id, barbearia_id)
            
            # 4. Se usuário não existe, cria novo
            if not usuario_existente:
                # Gera username único baseado no email
                username_base = dto.email.split('@')[0].lower().replace('.', '_')
                username = username_base
                counter = 1
                while Usuario.objects.filter(username=username).exists():
                    username = f"{username_base}_{counter}"
                    counter += 1
                
                # Gera senha temporária aleatória
                import secrets
                senha_temporaria = secrets.token_urlsafe(12)
                
                usuario = Usuario.objects.create_user(
                    username=username,
                    email=dto.email,
                    password=senha_temporaria,
                    cpf=dto.cpf,
                    tipo_usuario='BARBEIRO',
                    telefone=dto.telefone,
                    first_name=dto.nome_completo.split()[0] if dto.nome_completo else '',
                    last_name=' '.join(dto.nome_completo.split()[1:]) if len(dto.nome_completo.split()) > 1 else ''
                )
                
                logger.info(f"Novo usuário BARBEIRO criado: {usuario.id} | {usuario.email}")
            
            # 5. Cria convite pendente
            convite = self.convite_repository.create(
                dto=dto,
                barbearia_id=barbearia_id,
                usuario_id=usuario.id,
                criado_por=user_id
            )
            
            # 6. Envia email via Brevo
            barbearia = Barbearia.objects.get(id=barbearia_id)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            
            email_enviado = BrevoEmailService.enviar_convite_profissional(
                nome_barbeiro=dto.nome_completo,
                email_barbeiro=dto.email,
                nome_barbearia=barbearia.nome_comercial,
                comissao_percentual=dto.comissao_percentual,
                token=convite.token,
                frontend_url=frontend_url
            )
            
            # 7. Monta mensagem de resposta
            if usuario_existente:
                mensagem = f"Convite enviado para {dto.email}. O barbeiro já possui conta e receberá uma notificação para aceitar o vínculo."
            else:
                mensagem = f"Conta criada para {dto.email} e convite enviado. O barbeiro receberá um email com instruções para criar sua senha e aceitar o vínculo."
            
            logger.info(
                f"Convite criado: {convite.id} | Barbeiro: {dto.email} | "
                f"Barbearia: {barbearia.nome_comercial} | Email enviado: {email_enviado}"
            )
            
            response_dto = self._to_convite_response_dto(convite)
            
            return ServiceResultSingleDTO(
                success=True,
                data=response_dto,
                message=mensagem
            )
        
        except ConviteDuplicadoException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except ProfissionalJaVinculadoException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except DomainException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao criar convite: {e}")
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar convite"
            )
    
    def aceitar_convite(self, token: str) -> ServiceResultSingleDTO:
        """
        Aceita convite e cria vínculo profissional.
        
        Fluxo:
        1. Busca convite por token
        2. Valida se o convite é válido (não expirado, não aceito/recusado)
        3. Verifica se já é profissional nesta barbearia
        4. Cria vínculo profissional
        5. Marca convite como aceito
        """
        try:
            # 1. Busca convite por token
            convite = self.convite_repository.get_by_token_or_raise(token)
            
            # 2. Valida se o convite é válido
            if not convite.is_valido():
                if convite.status == ConviteProfissional.STATUS_ACEITO:
                    raise ConviteJaRespondidoException(convite.id, 'ACEITO')
                elif convite.status == ConviteProfissional.STATUS_RECUSADO:
                    raise ConviteJaRespondidoException(convite.id, 'RECUSADO')
                else:
                    raise ConviteExpiradoException(convite.id)
            
            # 3. Verifica se já é profissional nesta barbearia
            if self.profissional_repository.exists_by_usuario_na_barbearia(
                convite.usuario_id, convite.barbearia_id
            ):
                convite.aceitar()  # Marca como aceito mesmo assim
                return ServiceResultSingleDTO(
                    success=True,
                    message="Você já está vinculado a esta barbearia.",
                    data=ConviteAceiteResponseDTO(
                        success=True,
                        message="Vínculo já existente",
                        profissional_id=None,
                        barbearia_id=convite.barbearia_id
                    )
                )
            
            # 4. Cria vínculo profissional
            profissional_dto = ProfissionalCreateDTO(
                usuario_id=convite.usuario_id,
                comissao_percentual=convite.comissao_percentual,
                ativo=True
            )
            
            profissional = self.profissional_repository.create(
                dto=profissional_dto,
                barbearia_id=convite.barbearia_id
            )
            
            # 5. Marca convite como aceito
            convite.aceitar()
            
            logger.info(
                f"Convite aceito: {convite.id} | Profissional: {profissional.id} | "
                f"Barbearia: {convite.barbearia_id}"
            )
            
            return ServiceResultSingleDTO(
                success=True,
                message="Convite aceito com sucesso! Você agora é profissional desta barbearia.",
                data=ConviteAceiteResponseDTO(
                    success=True,
                    message="Convite aceito",
                    profissional_id=profissional.id,
                    barbearia_id=convite.barbearia_id
                )
            )
        
        except ConviteNotFoundException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except ConviteJaRespondidoException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except ConviteExpiradoException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except DomainException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao aceitar convite: {e}")
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao aceitar convite"
            )
    
    def recusar_convite(self, token: str) -> ServiceResultMessageDTO:
        """
        Recusa convite.
        """
        try:
            convite = self.convite_repository.get_by_token_or_raise(token)
            
            if not convite.is_valido():
                if convite.status == ConviteProfissional.STATUS_RECUSADO:
                    raise ConviteJaRespondidoException(convite.id, 'RECUSADO')
                elif convite.status == ConviteProfissional.STATUS_ACEITO:
                    raise ConviteJaRespondidoException(convite.id, 'ACEITO')
                else:
                    raise ConviteExpiradoException(convite.id)
            
            convite.recusar()
            
            logger.info(f"Convite recusado: {convite.id}")
            
            return ServiceResultMessageDTO(
                success=True,
                message="Convite recusado com sucesso."
            )
        
        except ConviteNotFoundException as e:
            return ServiceResultMessageDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except ConviteJaRespondidoException as e:
            return ServiceResultMessageDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except ConviteExpiradoException as e:
            return ServiceResultMessageDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.exception(f"Erro ao recusar convite: {e}")
            return ServiceResultMessageDTO(
                success=False,
                error="Erro interno ao recusar convite"
            )
    
    def listar_convites(
        self,
        barbearia_id: UUID,
        status: Optional[str] = None,
    ) -> ServiceResultListDTO:
        """
        Lista convites de uma barbearia (apenas DONO pode acessar).
        """
        try:
            convites = self.convite_repository.get_all_by_barbearia(barbearia_id, status)
            response_dtos = [self._to_convite_response_dto(c) for c in convites]
            
            return ServiceResultListDTO(success=True, data=response_dtos)
        
        except Exception as e:
            logger.exception(f"Erro ao listar convites: {e}")
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao listar convites"
            )
    
    def _to_convite_response_dto(self, convite: ConviteProfissional) -> ConviteProfissionalResponseDTO:
        """Converte model ConviteProfissional para DTO."""
        return ConviteProfissionalResponseDTO(
            id=convite.id,
            barbearia_id=convite.barbearia_id,
            usuario_id=convite.usuario_id,
            nome_completo=convite.nome_completo,
            email=convite.email,
            cpf=convite.cpf,
            telefone=convite.telefone,
            comissao_percentual=convite.comissao_percentual,
            status=convite.status,
            data_criacao=convite.data_criacao,
            data_expiracao=convite.data_expiracao
        )