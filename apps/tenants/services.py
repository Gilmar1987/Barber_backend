# [Domínio: tenants] [Skill: service]
"""
📖 MANIFESTO (Skill 03 - Service):
"Toda a inteligência reside no Service ou em handlers de eventos assíncronos."

📖 MANIFESTO (Negative Constraints):
"PROIBIDO acessar `request` em Services, Selectors ou Repositories"
"PROIBIDO vazar dicionários primitivos (request.data) para o Service"

📖 MANIFESTO (Seção 5 - EDA):
"Desacoplamento por Eventos: Lógicas secundárias operam de forma assíncrona.
Handlers assíncronos gerenciados por Celery + Redis escutam esse evento."

📖 MANIFESTO (LGPD Compliance):
"dados sensíveis mascarados em logs e respostas"

✅ Regras seguidas:
- Services recebem DTOs Pydantic (não Dict)
- Services retornam DTOs específicos (sem Any)
- Services NÃO acessam request HTTP
- Services delegam persistência ao Repository
- Services validam regras de negócio (ex: CNPJ duplicado)
- Services disparam eventos via dispatch_event
- Services mascaram dados sensíveis (CNPJ)
- Trilha de auditoria (user_id) passada explicitamente
"""
import logging
from typing import Optional
from uuid import UUID

from apps.tenants.dtos import (
    BarbeariaCreateDTO,
    BarbeariaListDTO,
    BarbeariaListWithDistanceDTO,
    BarbeariaResponseDTO,
    BarbeariaUpdateDTO,
    ProximidadeSearchDTO,
    ServiceResultListDTO,
    ServiceResultMessageDTO,
    ServiceResultSingleDTO,
)
from apps.tenants.repository import BarbeariaRepository
from common.events import EventType, dispatch_event
from common.exceptions import (
    BarbeariaNotFoundException,
    DomainException,
    DuplicateResourceException,
)

logger = logging.getLogger(__name__)


class BarbeariaService:
    """
    Service para operações com Barbearias (Tenants).
    Contém toda a lógica de negócio relacionada a barbearias.
    """
    
    def __init__(self, repository: Optional[BarbeariaRepository] = None):
        self.repository = repository or BarbeariaRepository()
    
    # ═══════════════════════════════════════════════════════════
    # CRIAR BARBEARIA
    # ═══════════════════════════════════════════════════════════
    
    def criar_barbearia(
        self,
        dto: BarbeariaCreateDTO,
        user_id: Optional[UUID] = None
    ) -> ServiceResultSingleDTO:
        """
        Cria nova barbearia com validações de negócio.
        
        📖 MANIFESTO: "Services validam regras de negócio"
        - Verifica duplicidade de CNPJ ANTES de persistir
        - Dispara evento TENANT_CREATED para handlers assíncronos
        - Mascara CNPJ na resposta (LGPD)
        """
        try:
            # 1. Validação de negócio: CNPJ único globalmente
            if self.repository.exists_by_cnpj(dto.cnpj):
                raise DuplicateResourceException('cnpj', dto.cnpj)
            
            # 2. Persistência via Repository (camada de escrita)
            barbearia = self.repository.create(dto, created_by=user_id)
            
            logger.info(
                f"Barbearia criada: {barbearia.id} | "
                f"CNPJ: {barbearia.get_cnpj_masked()}"
            )
            
            response_dto = self._to_response_dto(barbearia)
            
            result = ServiceResultSingleDTO(success=True, data=response_dto)
            
            try:
                dispatch_event(
                    event_type=EventType.TENANT_CREATED,
                    tenant_id=barbearia.id,
                    user_id=user_id or barbearia.id,
                    data={
                        'barbearia_id': str(barbearia.id),
                        'cnpj_masked': barbearia.get_cnpj_masked(),
                        'nome_comercial': barbearia.nome_comercial,
                        'cidade': barbearia.cidade,
                        'estado': barbearia.estado,
                    }
                )
            except Exception as e:
                logger.error(f"Falha ao disparar evento TENANT_CREATED: {e}", exc_info=True)
            
            return result
        
        except DuplicateResourceException as e:
            logger.warning(f"CNPJ duplicado: {e.details}")
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
            logger.error(f"Erro ao criar barbearia: {e}", exc_info=True)
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar barbearia"
            )
    
    # ═══════════════════════════════════════════════════════════
    # OBTER BARBEARIA
    # ═══════════════════════════════════════════════════════════
    
    def obter_barbearia(self, barbearia_id: UUID) -> ServiceResultSingleDTO:
        """Retorna dados de uma barbearia específica."""
        try:
            barbearia = self.repository.get_by_id_or_raise(barbearia_id)
            response_dto = self._to_response_dto(barbearia)
            
            return ServiceResultSingleDTO(
                success=True,
                data=response_dto
            )
        
        except BarbeariaNotFoundException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.error(f"Erro ao obter barbearia: {e}", exc_info=True)
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao obter barbearia"
            )
    
    # ═══════════════════════════════════════════════════════════
    # ATUALIZAR BARBEARIA
    # ═══════════════════════════════════════════════════════════
    
    def atualizar_barbearia(
        self,
        barbearia_id: UUID,
        dto: BarbeariaUpdateDTO,
        updated_by: Optional[UUID] = None
    ) -> ServiceResultSingleDTO:
        """
        Atualiza barbearia existente com validações de negócio.
        Dispara evento TENANT_UPDATED.
        """
        try:
            # 1. Busca barbearia (lança exception se não existir)
            barbearia = self.repository.get_by_id_or_raise(barbearia_id)
            
            # 2. Persistência via Repository
            updated_barbearia = self.repository.update(
                barbearia, dto, updated_by=updated_by
            )
            
            logger.info(f"Barbearia atualizada: {updated_barbearia.id}")
            
            response_dto = self._to_response_dto(updated_barbearia)
            
            result = ServiceResultSingleDTO(success=True, data=response_dto)
            
            try:
                dispatch_event(
                    event_type=EventType.TENANT_UPDATED,
                    tenant_id=updated_barbearia.id,
                    user_id=updated_by or updated_barbearia.id,
                    data={
                        'barbearia_id': str(updated_barbearia.id),
                        'fields_updated': [
                            field for field, value in dto.model_dump().items()
                            if value is not None
                        ]
                    }
                )
            except Exception as e:
                logger.error(f"Falha ao disparar evento TENANT_UPDATED: {e}", exc_info=True)
            
            return result
        
        except BarbeariaNotFoundException as e:
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
            logger.error(f"Erro ao atualizar barbearia: {e}", exc_info=True)
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao atualizar barbearia"
            )
    
    # ═══════════════════════════════════════════════════════════
    # LISTAR BARBEARIAS
    # ═══════════════════════════════════════════════════════════
    
    def listar_barbearias(self) -> ServiceResultListDTO:
        """Lista todas as barbearias ativas."""
        try:
            barbearias = self.repository.get_all_active()
            
            response_dtos = [
                self._to_list_dto(barbearia)
                for barbearia in barbearias
            ]
            
            return ServiceResultListDTO(
                success=True,
                data=response_dtos
            )
        
        except Exception as e:
            logger.error(f"Erro ao listar barbearias: {e}", exc_info=True)
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao listar barbearias"
            )
    
    # ═══════════════════════════════════════════════════════════
    # BUSCAR POR PROXIMIDADE
    # ═══════════════════════════════════════════════════════════
    
    def buscar_por_proximidade(
        self,
        search_dto: ProximidadeSearchDTO
    ) -> ServiceResultListDTO:
        """
        Busca barbearias por proximidade geográfica.
        
        📖 MANIFESTO: "Usar GEOGRAPHY(Point, 4326) para cálculos em metros reais"
        Retorna barbearias dentro do raio especificado, ordenadas por distância.
        """
        try:
            barbearias = self.repository.buscar_por_proximidade(
                latitude=search_dto.latitude,
                longitude=search_dto.longitude,
                raio_km=search_dto.raio_km
            )
            
            response_dtos = []
            for barbearia in barbearias:
                distancia_metros = None
                distancia = getattr(barbearia, 'distancia', None)
                if distancia is not None:
                    try:
                        distancia_metros = round(float(distancia.m), 2)
                    except (AttributeError, TypeError, ValueError):
                        distancia_metros = round(float(distancia), 2)
                response_dtos.append(
                    self._to_list_with_distance_dto(barbearia, distancia_metros)
                )
            
            logger.info(
                f"Busca por proximidade: {len(response_dtos)} barbearias "
                f"encontradas em raio de {search_dto.raio_km}km"
            )
            
            return ServiceResultListDTO(
                success=True,
                data=response_dtos
            )
        
        except Exception as e:
            logger.error(f"Erro ao buscar por proximidade: {e}", exc_info=True)
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao buscar barbearias por proximidade"
            )
    
    # ═══════════════════════════════════════════════════════════
    # SOFT DELETE
    # ═══════════════════════════════════════════════════════════
    
    def deletar_barbearia(
        self,
        barbearia_id: UUID,
        deleted_by: Optional[UUID] = None
    ) -> ServiceResultMessageDTO:
        """
        Realiza soft delete da barbearia.
        
        📖 MANIFESTO: "Soft Delete em entidades críticas"
        Barbearia é entidade crítica (é o próprio tenant), então
        apenas soft delete é permitido.
        """
        try:
            barbearia = self.repository.get_by_id_or_raise(barbearia_id)
            
            self.repository.soft_delete(barbearia, deleted_by=deleted_by)
            
            # EDA: Dispara evento assíncrono
            dispatch_event(
                event_type=EventType.TENANT_UPDATED,
                tenant_id=barbearia_id,
                user_id=deleted_by or barbearia_id,
                data={
                    'barbearia_id': str(barbearia_id),
                    'action': 'soft_deleted'
                }
            )
            
            logger.info(f"Barbearia deletada (soft): {barbearia_id}")
            
            return ServiceResultMessageDTO(
                success=True,
                message='Barbearia excluída com sucesso'
            )
        
        except BarbeariaNotFoundException as e:
            return ServiceResultMessageDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.error(f"Erro ao deletar barbearia: {e}", exc_info=True)
            return ServiceResultMessageDTO(
                success=False,
                error="Erro interno ao deletar barbearia"
            )
    
    # ═══════════════════════════════════════════════════════════
    # MÉTODOS PRIVADOS (Conversão Model → DTO)
    # ═══════════════════════════════════════════════════════════
    
    def _to_response_dto(self, barbearia) -> BarbeariaResponseDTO:
        """
        Converte model Barbearia para BarbeariaResponseDTO.
        
        📖 MANIFESTO (LGPD): CNPJ mascarado na resposta.
        📖 MANIFESTO (GEOGRAPHY): Extrai lat/long do Point PostGIS (y=lat, x=lon).
        """
        return BarbeariaResponseDTO(
            id=barbearia.id,
            nome_comercial=barbearia.nome_comercial,
            cnpj_masked=barbearia.get_cnpj_masked(),
            cep=barbearia.cep,
            logradouro=barbearia.logradouro,
            numero=barbearia.numero,
            complemento=barbearia.complemento,
            bairro=barbearia.bairro,
            cidade=barbearia.cidade,
            estado=barbearia.estado,
            latitude=barbearia.localizacao.y,
            longitude=barbearia.localizacao.x,
            telefone=barbearia.telefone,
            email=barbearia.email,
            ativo=barbearia.ativo,
            is_deleted=barbearia.is_deleted,
            created_at=barbearia.created_at.isoformat(),
            updated_at=barbearia.updated_at.isoformat(),
        )
    
    def _to_list_dto(self, barbearia) -> BarbeariaListDTO:
        """
        Converte model Barbearia para BarbeariaListDTO (versão resumida).
        
        📖 MANIFESTO (LGPD): CNPJ mascarado na resposta.
        """
        return BarbeariaListDTO(
            id=barbearia.id,
            nome_comercial=barbearia.nome_comercial,
            cnpj_masked=barbearia.get_cnpj_masked(),
            cidade=barbearia.cidade,
            estado=barbearia.estado,
            telefone=barbearia.telefone,
            ativo=barbearia.ativo,
            is_deleted=barbearia.is_deleted,
        )
    
    def _to_list_with_distance_dto(self, barbearia, distancia_metros: Optional[float]) -> BarbeariaListWithDistanceDTO:
        """Converte model Barbearia para BarbeariaListWithDistanceDTO (com distância)."""
        return BarbeariaListWithDistanceDTO(
            id=barbearia.id,
            nome_comercial=barbearia.nome_comercial,
            cnpj_masked=barbearia.get_cnpj_masked(),
            cidade=barbearia.cidade,
            estado=barbearia.estado,
            telefone=barbearia.telefone,
            ativo=barbearia.ativo,
            is_deleted=barbearia.is_deleted,
            distancia_metros=distancia_metros,
        )
