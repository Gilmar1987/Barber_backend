# [Domínio: operacional] [Skill: repository]
"""
📖 MANIFESTO (Skill 02 - Repository):
"Toda persistência e leitura devem passar estritamente pela camada de Repository."

📖 MANIFESTO (Negative Constraints):
"PROIBIDO acessar `request` em Services, Selectors ou Repositories"
"PROIBIDO realizar consultas diretas ao banco utilizando managers padrões
(ex: .objects.all()) em Service ou Views."

📖 MANIFESTO (Integridade de Dados - PDF Documento 3):
"ON DELETE CASCADE: Se a barbearia sai, serviços e profissionais saem"
"ON DELETE PROTECT: Serviço com agendamentos CONCLUIDOS não pode ser deletado"

✅ Regras seguidas:
- Todas as queries passam pelo Repository
- Usa DTOs Pydantic (sem Dict[str, Any])
- Transações atômicas para operações críticas
- update_fields explícito no update
- Multi-tenancy: TODO query filtra por barbearia_id
- Campo 'ativo' para desativação lógica (sem hard delete)
- Imports no topo do arquivo (PEP 8)
"""
from typing import List, Optional
from uuid import UUID

from django.db import transaction

from apps.operacional.dtos import ProfissionalCreateDTO, ServicoCreateDTO, ServicoUpdateDTO, ProfissionalUpdateDTO
from apps.operacional.models import Profissional, Servico
from common.exceptions import (
    DuplicateResourceException,
    ProfissionalDuplicadoException,
    ProfissionalNotFoundException,
    ServicoNotFoundException,
)


# ═══════════════════════════════════════════════════════════
# REPOSITÓRIO DE SERVIÇO
# ═══════════════════════════════════════════════════════════

class ServicoRepository:
    """
    Repositório para operações com o modelo Servico.
    Segue o padrão de isolamento de camadas e multi-tenancy.
    """
    
    @staticmethod
    def get_by_id(servico_id: int, barbearia_id: UUID) -> Optional[Servico]:
        """
        Busca serviço por ID, filtrando por barbearia (multi-tenancy).
        """
        try:
            return Servico.objects.get(id=servico_id, barbearia_id=barbearia_id)
        except Servico.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id_or_raise(servico_id: int, barbearia_id: UUID) -> Servico:
        """
        Busca serviço por ID ou lança ServicoNotFoundException.
        """
        servico = ServicoRepository.get_by_id(servico_id, barbearia_id)
        if not servico:
            raise ServicoNotFoundException(servico_id, barbearia_id)
        return servico
    
    @staticmethod
    def get_all_by_barbearia(
        barbearia_id: UUID,
        ativo_only: bool = True
    ) -> List[Servico]:
        """
        Lista todos os serviços de uma barbearia.
        """
        queryset = Servico.objects.filter(barbearia_id=barbearia_id)
        if ativo_only:
            queryset = queryset.filter(ativo=True)
        return list(queryset.order_by('nome'))
    
    @staticmethod
    def create(
        dto: ServicoCreateDTO,
        barbearia_id: UUID,
        created_by: Optional[UUID] = None
    ) -> Servico:
        """
        Cria novo serviço com transação atômica.
        """
        with transaction.atomic():
            servico = Servico.objects.create(
                barbearia_id=barbearia_id,
                nome=dto.nome,
                preco=dto.preco,
                duracao_minutos=dto.duracao_minutos,
                ativo=dto.ativo,
            )
            return servico
    
    @staticmethod
    def update(
        servico: Servico,
        dto: ServicoUpdateDTO,
        updated_by: Optional[UUID] = None
    ) -> Servico:
        """
        Atualiza serviço existente com update_fields explícito.
        """
        update_fields = []
        
        if dto.nome is not None:
            servico.nome = dto.nome
            update_fields.append('nome')
        if dto.preco is not None:
            servico.preco = dto.preco
            update_fields.append('preco')
        if dto.duracao_minutos is not None:
            servico.duracao_minutos = dto.duracao_minutos
            update_fields.append('duracao_minutos')
        if dto.ativo is not None:
            servico.ativo = dto.ativo
            update_fields.append('ativo')
        
        if update_fields:
            servico.save(update_fields=update_fields)
        
        return servico
    
    @staticmethod
    def toggle_ativo(servico: Servico) -> Servico:
        """
        Alterna o status ativo/inativo do serviço.
        """
        servico.ativo = not servico.ativo
        servico.save(update_fields=['ativo'])
        return servico
    
    @staticmethod
    def has_agendamentos_concluidos(servico_id: int) -> bool:
        """
        Verifica se o serviço possui agendamentos com status CONCLUIDO.
        Usado para proteção de histórico de BI (ON DELETE PROTECT).
        
        ⚠️ Este método será útil quando o domínio agenda for implementado.
        Por enquanto, retorna False como placeholder.
        """
        # TODO: Implementar quando agenda_agendamento existir
        # from apps.agenda.models import Agendamento
        # return Agendamento.objects.filter(
        #     servico_id=servico_id,
        #     status='CONCLUIDO'
        # ).exists()
        return False


# ═══════════════════════════════════════════════════════════
# REPOSITÓRIO DE PROFISSIONAL
# ═══════════════════════════════════════════════════════════

class ProfissionalRepository:
    """
    Repositório para operações com o modelo Profissional.
    Segue o padrão de isolamento de camadas e multi-tenancy.
    """
    
    @staticmethod
    def get_by_id(profissional_id: int, barbearia_id: UUID) -> Optional[Profissional]:
        """
        Busca profissional por ID, filtrando por barbearia (multi-tenancy).
        """
        try:
            return Profissional.objects.get(id=profissional_id, barbearia_id=barbearia_id)
        except Profissional.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id_or_raise(profissional_id: int, barbearia_id: UUID) -> Profissional:
        """
        Busca profissional por ID ou lança ProfissionalNotFoundException.
        """
        profissional = ProfissionalRepository.get_by_id(profissional_id, barbearia_id)
        if not profissional:
            raise ProfissionalNotFoundException(profissional_id, barbearia_id)
        return profissional
    
    @staticmethod
    def get_by_usuario(usuario_id: UUID, barbearia_id: UUID) -> Optional[Profissional]:
        """
        Busca profissional por usuário, filtrando por barbearia.
        """
        try:
            return Profissional.objects.get(usuario_id=usuario_id, barbearia_id=barbearia_id)
        except Profissional.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_by_barbearia(
        barbearia_id: UUID,
        ativo_only: bool = True
    ) -> List[Profissional]:
        """
        Lista todos os profissionais de uma barbearia.
        """
        queryset = Profissional.objects.filter(barbearia_id=barbearia_id)
        if ativo_only:
            queryset = queryset.filter(ativo=True)
        return list(queryset.select_related('usuario').order_by('usuario__username'))
    
    @staticmethod
    def exists_by_usuario_na_barbearia(usuario_id: UUID, barbearia_id: UUID) -> bool:
        """
        Verifica se usuário já é profissional nesta barbearia.
        """
        return Profissional.objects.filter(
            usuario_id=usuario_id,
            barbearia_id=barbearia_id
        ).exists()
    
    @staticmethod
    def create(
        dto: ProfissionalCreateDTO,
        barbearia_id: UUID,
        created_by: Optional[UUID] = None
    ) -> Profissional:
        """
        Cria novo vínculo profissional com validações de negócio.
        
        Validações:
        1. Usuário deve existir e ser do tipo BARBEIRO
        2. Usuário não pode ser profissional nesta barbearia (unicidade)
        """
        with transaction.atomic():
            # Validação: usuário não pode ser profissional nesta barbearia duas vezes
            if ProfissionalRepository.exists_by_usuario_na_barbearia(dto.usuario_id, barbearia_id):
                raise ProfissionalDuplicadoException(dto.usuario_id, barbearia_id)

            profissional = Profissional.objects.create(
                barbearia_id=barbearia_id,
                usuario_id=dto.usuario_id,
                comissao_percentual=dto.comissao_percentual,
                ativo=dto.ativo,
            )
            return profissional
    
    @staticmethod
    def update(
        profissional: Profissional,
        dto: ProfissionalUpdateDTO,
        updated_by: Optional[UUID] = None
    ) -> Profissional:
        """
        Atualiza profissional existente com update_fields explícito.
        """
        update_fields = []
        
        if dto.comissao_percentual is not None:
            profissional.comissao_percentual = dto.comissao_percentual
            update_fields.append('comissao_percentual')
        if dto.ativo is not None:
            profissional.ativo = dto.ativo
            update_fields.append('ativo')
        
        if update_fields:
            profissional.save(update_fields=update_fields)
        
        return profissional
    
    @staticmethod
    def toggle_ativo(profissional: Profissional) -> Profissional:
        """
        Alterna o status ativo/inativo do profissional.
        """
        profissional.ativo = not profissional.ativo
        profissional.save(update_fields=['ativo'])
        return profissional