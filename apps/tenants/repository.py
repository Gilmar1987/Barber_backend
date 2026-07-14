# [Domínio: tenants] [Skill: repository]
"""
📖 MANIFESTO (Skill 02 - Repository):
"Toda persistência e leitura devem passar estritamente pela camada de Repository."

📖 MANIFESTO (Negative Constraints):
"PROIBIDO acessar `request` em Services, Selectors ou Repositories"
"PROIBIDO realizar consultas diretas ao banco utilizando managers padrões
(ex: .objects.all()) em Service ou Views."

📖 MANIFESTO (Isolamento de Camadas):
"Services podem acessar `Selectors`, `Repositories`, `Events`"

📖 MANIFESTO (Soft Delete):
"Soft Delete em entidades críticas"

✅ Regras seguidas:
- Todas as queries passam pelo Repository
- Usa DTOs Pydantic (sem Dict[str, Any])
- Transações atômicas para operações críticas
- Trilha de auditoria (created_by, updated_by, deleted_by)
- Não acessa request HTTP
- Hard delete removido — Barbearia é entidade crítica (é o próprio tenant)
- update com update_fields explícito (evita sobrescrever campos não alterados)
- Imports no topo do arquivo (não dentro de métodos)

⚠️ NOTA ARQUITETURAL:
Barbearia herda de models.Model (não TenantBaseModel) porque ela É o tenant.
Não faz sentido filtrar barbearia por tenant_id — ela mesma é o tenant_id.
O isolamento multi-tenant se aplica às entidades DENTRO de cada barbearia
(agendamentos, serviços, profissionais), não à própria barbearia.
Para busca global (ex: marketplace), usa-se unscoped_objects (UnscopedManager).
"""
from typing import List, Optional
from uuid import UUID

from django.db import IntegrityError, transaction

from apps.tenants.dtos import BarbeariaCreateDTO, BarbeariaUpdateDTO
from apps.tenants.models import Barbearia
from common.exceptions import BarbeariaNotFoundException, DuplicateResourceException


class BarbeariaRepository:
    """
    Repositório para operações com o modelo Barbearia.
    Segue o padrão de isolamento de camadas.
    """

    @staticmethod
    def get_by_id(barbearia_id: UUID) -> Optional[Barbearia]:
        """Busca barbearia ativa por ID."""
        try:
            return Barbearia.objects.get(id=barbearia_id, is_deleted=False)
        except Barbearia.DoesNotExist:
            return None

    @staticmethod
    def get_by_id_or_raise(barbearia_id: UUID) -> Barbearia:
        """Busca barbearia por ID ou lança BarbeariaNotFoundException."""
        barbearia = BarbeariaRepository.get_by_id(barbearia_id)
        if not barbearia:
            raise BarbeariaNotFoundException(str(barbearia_id))
        return barbearia

    @staticmethod
    def get_by_cnpj(cnpj: str) -> Optional[Barbearia]:
        """
        Busca barbearia por CNPJ.
        CNPJ é único globalmente — busca sem filtro de tenant.
        """
        try:
            return Barbearia.objects.get(cnpj=cnpj, is_deleted=False)
        except Barbearia.DoesNotExist:
            return None

    @staticmethod
    def get_all_active() -> List[Barbearia]:
        """Lista todas as barbearias ativas e não deletadas."""
        return list(Barbearia.objects.filter(ativo=True, is_deleted=False))

    @staticmethod
    def get_all() -> List[Barbearia]:
        """Alias de get_all_active() para compatibilidade."""
        return BarbeariaRepository.get_all_active()

    @staticmethod
    def create(dto: BarbeariaCreateDTO, created_by: Optional[UUID] = None) -> Barbearia:
        """
        Cria nova barbearia com transação atômica.
        Point(longitude, latitude) — ordem correta para PostGIS GEOGRAPHY.
        """
        with transaction.atomic():
            try:
                barbearia = Barbearia(
                    nome_comercial=dto.nome_comercial,
                    cnpj=dto.cnpj,
                    cep=dto.cep,
                    logradouro=dto.logradouro,
                    numero=dto.numero,
                    complemento=dto.complemento,
                    bairro=dto.bairro,
                    cidade=dto.cidade,
                    estado=dto.estado,
                    telefone=dto.telefone,
                    email=dto.email,
                    created_by_id=created_by,
                )
                barbearia.save()
                return barbearia

            except IntegrityError as e:
                error_msg = str(e).lower()
                if 'cnpj' in error_msg:
                    raise DuplicateResourceException('cnpj', dto.cnpj)
                raise

    @staticmethod
    def update(
        barbearia: Barbearia,
        dto: BarbeariaUpdateDTO,
        updated_by: Optional[UUID] = None
    ) -> Barbearia:
        """
        Atualiza barbearia existente com transação atômica.
        Usa update_fields explícito para atualizar apenas campos alterados.
        """
        with transaction.atomic():
            fields_to_update = ['updated_by']

            if dto.nome_comercial is not None:
                barbearia.nome_comercial = dto.nome_comercial
                fields_to_update.append('nome_comercial')
            if dto.cep is not None:
                barbearia.cep = dto.cep
                fields_to_update.append('cep')
            if dto.logradouro is not None:
                barbearia.logradouro = dto.logradouro
                fields_to_update.append('logradouro')
            if dto.numero is not None:
                barbearia.numero = dto.numero
                fields_to_update.append('numero')
            if dto.complemento is not None:
                barbearia.complemento = dto.complemento
                fields_to_update.append('complemento')
            if dto.bairro is not None:
                barbearia.bairro = dto.bairro
                fields_to_update.append('bairro')
            if dto.cidade is not None:
                barbearia.cidade = dto.cidade
                fields_to_update.append('cidade')
            if dto.estado is not None:
                barbearia.estado = dto.estado
                fields_to_update.append('estado')
            # localizacao (GIS) removido — campo não existe no modelo atual
            if dto.telefone is not None:
                barbearia.telefone = dto.telefone
                fields_to_update.append('telefone')
            if dto.email is not None:
                barbearia.email = dto.email
                fields_to_update.append('email')
            if dto.ativo is not None:
                barbearia.ativo = dto.ativo
                fields_to_update.append('ativo')

            barbearia.updated_by_id = updated_by
            barbearia.save(update_fields=fields_to_update)
            return barbearia

    @staticmethod
    def soft_delete(barbearia: Barbearia, deleted_by: Optional[UUID] = None) -> bool:
        """
        Marca barbearia como excluída (soft delete).
        Hard delete removido — Barbearia é entidade crítica (é o próprio tenant).

        📖 MANIFESTO: "Soft Delete em entidades críticas"
        """
        barbearia.soft_delete(user_id=deleted_by)
        return True

    @staticmethod
    def exists_by_cnpj(cnpj: str, exclude_id: Optional[UUID] = None) -> bool:
        """Verifica se CNPJ já existe globalmente (excluindo barbearia específica)."""
        queryset = Barbearia.objects.filter(cnpj=cnpj, is_deleted=False)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    @staticmethod
    def buscar_por_proximidade(
        latitude: float,
        longitude: float,
        raio_km: float = 10.0
    ) -> List[Barbearia]:
        """
        Busca barbearias ativas.

        ⚠️ NOTA: campo GIS 'localizacao' foi removido do modelo.
        Retorna todas as barbearias ativas sem filtro de proximidade.
        Para reativar busca geoespacial, reintegre django.contrib.gis e
        adicione o campo PointField ao modelo Barbearia.
        """
        return list(
            Barbearia.objects.filter(
                ativo=True,
                is_deleted=False,
            )
        )
