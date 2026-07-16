# [Domínio: core] [Skill: service]
"""
📖 MANIFESTO (Skill 03 - Service):
"Toda a inteligência reside no Service ou em handlers de eventos assíncronos."

✅ Regras seguidas:
- Services recebem DTOs Pydantic (não Dict)
- Services retornam DTOs específicos (sem Any)
- Services não acessam request HTTP
- Services disparam eventos via dispatch_event
"""
import logging
import requests
from typing import Optional, Dict
from decimal import Decimal
from django.conf import settings
from uuid import UUID

from apps.core.models import GeolocalizacaoCache

from apps.core.dtos import (
    ServiceResultListDTO,
    ServiceResultMessageDTO,
    ServiceResultSingleDTO,
    UsuarioCreateDTO,
    UsuarioResponseDTO,
    UsuarioUpdateDTO,
)
from apps.core.repository import UsuarioRepository
from common.events import EventType, dispatch_event
from common.exceptions import (
    DomainException,
    DuplicateResourceException,
    UserNotFoundException,
)

logger = logging.getLogger(__name__)


class UsuarioService:
    """Service para operações com usuários."""
    
    def __init__(self, repository: Optional[UsuarioRepository] = None):
        self.repository = repository or UsuarioRepository()
    
    def criar_usuario(
        self,
        dto: UsuarioCreateDTO,
        user_id: Optional[UUID] = None
    ) -> ServiceResultSingleDTO:
        """Cria novo usuário com validações de negócio."""
        try:
            if self.repository.exists_by_cpf(dto.cpf):
                raise DuplicateResourceException('cpf', dto.cpf)
            
            if self.repository.exists_by_email(dto.email):
                raise DuplicateResourceException('email', dto.email)
            
            user = self.repository.create(dto, created_by=user_id)
            
            logger.info(f"Usuário criado: {user.id}")
            
            response_dto = UsuarioResponseDTO(
                id=user.id,
                username=user.username,
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                email=user.email,
                cpf_masked=user.get_cpf_masked(),
                tipo_usuario=user.tipo_usuario,
                telefone=user.telefone,
                date_joined=user.date_joined.isoformat(),
            )
            
            result = ServiceResultSingleDTO(success=True, data=response_dto)
            
            # dispatch_event fora do bloco de persistência:
            # o usuário já foi commitado; falha no evento não reverte o dado.
            try:
                dispatch_event(
                    event_type=EventType.USER_CREATED,
                    tenant_id=user_id or user.id,
                    user_id=user.id,
                    data={
                        'user_id': str(user.id),
                        'username': user.username,
                        'email': user.email,
                        'tipo_usuario': user.tipo_usuario,
                    }
                )
            except Exception as e:
                logger.error(f"Falha ao disparar evento USER_CREATED: {e}", exc_info=True)
            
            return result
        
        except DomainException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}", exc_info=True)
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao criar usuário"
            )
    
    def atualizar_usuario(
        self,
        user_id: UUID,
        dto: UsuarioUpdateDTO,
        updated_by: Optional[UUID] = None
    ) -> ServiceResultSingleDTO:
        """Atualiza usuário existente com validações de negócio."""
        try:
            user = self.repository.get_by_id(user_id)
            if not user:
                raise UserNotFoundException(str(user_id))
            
            if dto.email and self.repository.exists_by_email(dto.email, exclude_id=user_id):
                raise DuplicateResourceException('email', dto.email)
            
            updated_user = self.repository.update(user, dto, updated_by=updated_by)
            
            logger.info(f"Usuário atualizado: {updated_user.id}")
            
            response_dto = UsuarioResponseDTO(
                id=updated_user.id,
                username=updated_user.username,
                first_name=updated_user.first_name or "",
                last_name=updated_user.last_name or "",
                email=updated_user.email,
                cpf_masked=updated_user.get_cpf_masked(),
                tipo_usuario=updated_user.tipo_usuario,
                telefone=updated_user.telefone,
                date_joined=updated_user.date_joined.isoformat(),
            )
            
            result = ServiceResultSingleDTO(success=True, data=response_dto)
            
            try:
                dispatch_event(
                    event_type=EventType.USER_UPDATED,
                    tenant_id=updated_by or updated_user.id,
                    user_id=updated_user.id,
                    data={
                        'user_id': str(updated_user.id),
                        'fields_updated': [
                            field for field, value in dto.model_dump().items()
                            if value is not None
                        ]
                    }
                )
            except Exception as e:
                logger.error(f"Falha ao disparar evento USER_UPDATED: {e}", exc_info=True)
            
            return result
        
        except UserNotFoundException as e:
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
            logger.error(f"Erro ao atualizar usuário: {e}", exc_info=True)
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao atualizar usuário"
            )
    
    def obter_usuario(self, user_id: UUID) -> ServiceResultSingleDTO:
        """Retorna dados de um usuário específico."""
        try:
            user = self.repository.get_by_id(user_id)
            if not user:
                raise UserNotFoundException(str(user_id))
            
            response_dto = UsuarioResponseDTO(
                id=user.id,
                username=user.username,
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                email=user.email,
                cpf_masked=user.get_cpf_masked(),
                tipo_usuario=user.tipo_usuario,
                telefone=user.telefone,
                date_joined=user.date_joined.isoformat(),
            )
            
            return ServiceResultSingleDTO(
                success=True,
                data=response_dto
            )
        
        except UserNotFoundException as e:
            return ServiceResultSingleDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.error(f"Erro ao obter usuário: {e}", exc_info=True)
            return ServiceResultSingleDTO(
                success=False,
                error="Erro interno ao obter usuário"
            )
    
    def listar_usuarios(
        self,
        tipo_usuario: Optional[str] = None
    ) -> ServiceResultListDTO:
        """Lista usuários, opcionalmente filtrando por tipo."""
        try:
            users = self.repository.get_all_by_tipo(tipo_usuario)
            
            response_dtos = [
                UsuarioResponseDTO(
                    id=user.id,
                    username=user.username,
                    first_name=user.first_name or "",
                    last_name=user.last_name or "",
                    email=user.email,
                    cpf_masked=user.get_cpf_masked(),
                    tipo_usuario=user.tipo_usuario,
                    telefone=user.telefone,
                    date_joined=user.date_joined.isoformat(),
                )
                for user in users
            ]
            
            return ServiceResultListDTO(
                success=True,
                data=response_dtos
            )
        
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}", exc_info=True)
            return ServiceResultListDTO(
                success=False,
                error="Erro interno ao listar usuários"
            )
    
    def deletar_usuario(
        self,
        user_id: UUID,
        deleted_by: Optional[UUID] = None
    ) -> ServiceResultMessageDTO:
        """Remove usuário do sistema."""
        try:
            user = self.repository.get_by_id(user_id)
            if not user:
                raise UserNotFoundException(str(user_id))
            
            self.repository.delete(user, deleted_by=deleted_by)
            
            logger.info(f"Usuário deletado: {user_id}")
            
            result = ServiceResultMessageDTO(success=True, message='Usuário removido com sucesso')
            
            try:
                dispatch_event(
                    event_type=EventType.USER_DELETED,
                    tenant_id=deleted_by or user_id,
                    user_id=user_id,
                    data={'user_id': str(user_id)}
                )
            except Exception as e:
                logger.error(f"Falha ao disparar evento USER_DELETED: {e}", exc_info=True)
            
            return result
        
        except UserNotFoundException as e:
            return ServiceResultMessageDTO(
                success=False,
                error=e.message,
                details=e.details
            )
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}", exc_info=True)
            return ServiceResultMessageDTO(
                success=False,
                error="Erro interno ao deletar usuário"
            )
        
class GeolocalizacaoService:
    """
    Service para operações com geolocalização e cache de CEP.
    """

    API_URL = "https://www.cepaberto.com/api/v3/cep"

    @staticmethod
    def obter_ou_criar_cache(
        cep: str,
        latitude_manual: Optional[float]=None,
        longitude_manual: Optional[float]=None
    ) -> Optional[Dict[str, float]]:
        """
        Obtém geolocalização de um CEP, usando cache local.
        Se não encontrado no cache, consulta API externa e salva no cache.
        Retorna dict com latitude e longitude ou None se falhar.
        

        """

        cep_limpo = ''.join(filter(str.isdigit, cep))
        # 1. Higienização
        if len(cep_limpo) != 8:
            logger.warning("CEP inválido: %s", cep)
            return None
        
        # 2. Busca no cache
        cache_item = GeolocalizacaoCache.objects.filter(cep=cep_limpo).first()
        if cache_item and cache_item.latitude is not None and cache_item.longitude is not None:
            return {"latitude": cache_item.latitude, "longitude": cache_item.longitude}
        
        # 3. Se manual, usa valores fornecidos
        if latitude_manual is not None and longitude_manual is not None:
            GeolocalizacaoCache.objects.update_or_create(
                cep=cep_limpo,
                defaults={
                    "latitude": latitude_manual,
                    "longitude": longitude_manual,
                    "cidade": "Manual",
                    "estado": "XX",
                }
            )
            logger.info("Geolocalização manual para CEP %s: (%f, %f)", cep_limpo, latitude_manual, longitude_manual)
            return {"latitude": float(latitude_manual), "longitude": float(longitude_manual)}
        
        # 4. Consulta API externa
        api_token = getattr(settings, 'CEP_ABERTO_TOKEN', None)        
            
        if not api_token:
            logger.error("CEP Aberto API token não configurado")
            return None
        
        try:
            headers = {
                "Authorization": f"Token token={api_token}",
                "Accept": "application/json"
            }
            response = requests.get(f"{GeolocalizacaoService.API_URL}/{cep_limpo}", headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
           
            if data and 'latitude' in data and 'longitude' in data:
                latitude = float(data['latitude'])
                longitude = float(data['longitude'])
                cidade = data.get('cidade', {}).get('nome', '')
                estado = data.get('estado', {}).get('sigla', '')

                # 5. Salva no cache
                GeolocalizacaoCache.objects.update_or_create(
                    cep=cep_limpo,
                    defaults={
                        "latitude": latitude,
                        "longitude": longitude,
                        "cidade": cidade,
                        "estado": estado,
                    }
                )
                logger.info("Geolocalização para CEP %s: (%f, %f), %s, %s", cep_limpo, latitude, longitude, cidade, estado)
                return {"latitude": latitude, "longitude": longitude}
            
        except requests.RequestException as e:
            logger.error(f"Erro ao consultar API CEP Aberto:{cep_limpo}, {e}", exc_info=True)

        return None