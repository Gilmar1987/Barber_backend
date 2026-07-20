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
from common.utils import mask_cnpj, mask_cpf

from django.db import DatabaseError, OperationalError
from django.contrib.gis.geos import Point
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
from apps.tenants.dtos import ServiceResultListWithDistanceDTO
from apps.core.service import GeolocalizacaoService

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

            # 2. Obter coordenadas: cache → API CEP Aberto → fallback manual
            coords = GeolocalizacaoService.obter_ou_criar_cache(
                cep=dto.cep,
                latitude_manual=dto.latitude,
                longitude_manual=dto.longitude,
            )

            # 3. Se nenhuma fonte retornou coords → solicita preenchimento manual
            if not coords:
                return ServiceResultSingleDTO(
                    success=False,
                    error=(
                        "Não foi possível obter as coordenadas automaticamente para o CEP informado. "
                        "Por favor, informe latitude e longitude manualmente."
                    ),
                    details={
                        "cep": dto.cep,
                        "requer_coordenadas_manuais": True,
                    },
                )

            # 4. Monta o ponto geográfico — Point(longitude, latitude) para PostGIS
            localizacao = Point(coords['longitude'], coords['latitude'], srid=4326)

            # 5. Persistência única via Repository (inclui o Point já resolvido)
            barbearia = self.repository.create(
                dto,
                localizacao=localizacao,
                created_by=user_id,
            )

            logger.info(
                "Barbearia criada: %s | CNPJ: %s | coords: (%.6f, %.6f)",
                barbearia.id,
                barbearia.get_cnpj_masked(),
                coords['latitude'],
                coords['longitude'],
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
                    },
                )
            except Exception:
                logging.exception('Falha ao disparar evento TENANT_CREATED')

            return result

        except DuplicateResourceException as e:
            logger.warning("CNPJ duplicado: %s", e.details)
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details,
            )
        except DomainException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details,
            )
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao criar barbearia')
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar barbearia",
            )
        except Exception:
            logging.exception('Erro inesperado ao criar barbearia')
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar barbearia",
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
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao obter barbearia')
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao obter barbearia"
            )
        except Exception:
            logging.exception('Erro inesperado ao obter barbearia')
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

            # 2. Recalcular coordenadas somente se CEP foi alterado
            localizacao = None
            if dto.cep is not None:
                coords = GeolocalizacaoService.obter_ou_criar_cache(
                    cep=dto.cep,
                    latitude_manual=dto.latitude,
                    longitude_manual=dto.longitude,
                )
                if not coords:
                    return ServiceResultSingleDTO(
                        success=False,
                        error=(
                            "Não foi possível obter as coordenadas para o novo CEP. "
                            "Por favor, informe latitude e longitude manualmente."
                        ),
                        details={
                            "cep": dto.cep,
                            "requer_coordenadas_manuais": True,
                        },
                    )
                localizacao = Point(coords['longitude'], coords['latitude'], srid=4326)

            # 3. Persistência via Repository (atualização parcial com update_fields)
            updated_barbearia = self.repository.update(
                barbearia,
                dto,
                localizacao=localizacao,
                updated_by=updated_by,
            )

            logger.info("Barbearia atualizada: %s", updated_barbearia.id)

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
                        ],
                    },
                )
            except Exception:
                logging.exception('Falha ao disparar evento TENANT_UPDATED')

            return result

        except BarbeariaNotFoundException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details,
            )
        except DomainException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details,
            )
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao atualizar barbearia')
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao atualizar barbearia",
            )
        except Exception:
            logging.exception('Erro inesperado ao atualizar barbearia')
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao atualizar barbearia",
            )
    
    # ═══════════════════════════════════════════════════════════
    # LISTAR BARBEARIAS
    # ═══════════════════════════════════════════════════════════
    
    def listar_barbearias(self, user_id: Optional[UUID] = None) -> ServiceResultListDTO:
        """
        Lista barbearias. 
        Se user_id for fornecido, lista apenas as criadas por ele.
        Caso contrário, lista todas as ativas (modo marketplace).
        """
        try:
            if user_id:
                # DONO quer ver TODAS as barbearias que ele criou
                barbearias = self.repository.get_all_by_created_by(user_id)
            else:
                # Cliente final quer ver TODAS as barbearias ativas do sistema
                barbearias = self.repository.get_all_active()
            
            response_dtos = [
                self._to_list_dto(barbearia)
                for barbearia in barbearias
            ]
            
            return ServiceResultListDTO(
                success=True,
                data=response_dtos
            )
        
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao listar barbearias')
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao listar barbearias"
            )
        except Exception:
            logging.exception('Erro inesperado ao listar barbearias')
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao listar barbearias"
            )
    
    # ═══════════════════════════════════════════════════════════
    # BUSCAR POR PROXIMIDADE
    # ═══════════════════════════════════════════════════════════
   
    # apps/tenants/services.py

    def buscar_por_proximidade(
        self,
        search_dto: ProximidadeSearchDTO
    ) -> ServiceResultListWithDistanceDTO:
        try:
            # Retorna lista de dicionários (devido ao .values() no Repository)
            barbearias_data = self.repository.buscar_por_proximidade(
                latitude=search_dto.latitude,
                longitude=search_dto.longitude,
                raio_km=search_dto.raio_km
            )
            
            response_dtos = []
            for b in barbearias_data:
                # Extrair distância do dicionário
                distancia_obj = b.get('distancia_metros')
                distancia_em_metros = float(distancia_obj.m) if distancia_obj and hasattr(distancia_obj, 'm') else (float(distancia_obj) if distancia_obj else None)
                
                # Regra LGPD: Mascarar CNPJ manualmente (pois 'b' é um dict, não um Model)
                cnpj = str(b.get('cnpj', ''))
                cnpj_masked = f"{cnpj[:2]}.***.***{cnpj[-1]}" if len(cnpj) >= 2 else "**.***.***"
                
                response_dtos.append(
                    BarbeariaListWithDistanceDTO(
                        id=b['id'],
                        nome_comercial=b['nome_comercial'],
                        #cnpj_masked=cnpj_masked,
                        cnpj_masked=mask_cnpj(cnpj),
                        cidade=b['cidade'],
                        estado=b['estado'],
                        telefone=b['telefone'],
                        ativo=b['ativo'],
                        is_deleted=b['is_deleted'],
                        distancia_metros=distancia_em_metros
                    )
                )
            
            logger.info(f"Busca por proximidade: {len(response_dtos)} barbearias encontradas.")
            
            return ServiceResultListWithDistanceDTO(
                success=True,
                data=response_dtos
            )
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao buscar barbearias por proximidade')
            return ServiceResultListWithDistanceDTO(
                success=False,
                error="Erro interno ao buscar barbearias por proximidade"
            )
        except Exception:
            logging.exception('Erro inesperado ao buscar barbearias por proximidade')
            return ServiceResultListWithDistanceDTO(
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
            
            try:
                dispatch_event(
                    event_type=EventType.TENANT_UPDATED,
                    tenant_id=barbearia_id,
                    user_id=deleted_by or barbearia_id,
                    data={
                        'barbearia_id': str(barbearia_id),
                        'action': 'soft_deleted'
                    }
                )
            except Exception:
                logging.exception('Falha ao disparar evento TENANT_UPDATED (soft_delete)')
            
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
        except (DatabaseError, OperationalError):
            logging.exception('Erro de banco ao deletar barbearia')
            return ServiceResultMessageDTO(
                success=False,
                error="Erro interno ao deletar barbearia"
            )
        except Exception:
            logging.exception('Erro inesperado ao deletar barbearia')
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
            # Extrai lat/lng reais do campo PostGIS (y=latitude, x=longitude)
            latitude=barbearia.localizacao.y if barbearia.localizacao else None,
            longitude=barbearia.localizacao.x if barbearia.localizacao else None,
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
