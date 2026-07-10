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
from typing import Optional
from uuid import UUID

from django.db import DatabaseError, OperationalError

from apps.operacional.dtos import (
    ProfissionalCreateDTO,
    ProfissionalResponseDTO,
    ProfissionalUpdateDTO,
    ServicoCreateDTO,
    ServicoResponseDTO,
    ServicoUpdateDTO,
    ServiceResultListDTO,
    ServiceResultMessageDTO,
    ServiceResultSingleDTO,
)
from apps.operacional.repository import ProfissionalRepository, ServicoRepository
from common.events import EventType, dispatch_event
from common.exceptions import (
    DomainException,
    ProfissionalDuplicadoException,
    ProfissionalNotFoundException,
    ServicoComHistoricoException,
    ServicoNotFoundException,
    UsuarioNaoBarbeiroException,
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
