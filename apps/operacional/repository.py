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
from datetime import date, time
from typing import List, Optional
from uuid import UUID

from django.db import transaction

from apps.operacional.dtos import (
    ConviteProfissionalCreateDTO,
    DiaIndisponivelCreateDTO,
    GradeHorariaCreateDTO,
    GradeHorariaUpdateDTO,
    IntervaloIndisponivelCreateDTO,
    ProfissionalCreateDTO,
    ProfissionalUpdateDTO,
    ServicoCreateDTO,
    ServicoUpdateDTO,
    ServicoProfissionalCreateDTO,
)
from apps.operacional.models import (
    ConviteProfissional,
    DiaIndisponivel,
    GradeHoraria,
    IntervaloIndisponivel,
    Profissional,
    Servico,
    ServicoProfissional,
)
from common.exceptions import (
    ConviteNotFoundException,
    DiaIndisponivelConflictException,
    DiaIndisponivelNotFoundException,
    DuplicateResourceException,
    GradeHorariaConflictException,
    GradeHorariaNotFoundException,
    IntervaloIndisponivelConflictException,
    IntervaloIndisponivelNotFoundException,
    ProfissionalDuplicadoException,
    ProfissionalNotFoundException,
    ServicoNotFoundException,
    ServicoProfissionalConflictException,
    UsuarioNaoBarbeiroException,
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
    
    @staticmethod
    def exists_by_nome_na_barbearia(nome: str, barbearia_id: UUID) -> bool:
        """Verifica se já existe um serviço com este nome nesta barbearia."""
        return Servico.objects.filter(
            nome__iexact=nome.strip(),
            barbearia_id=barbearia_id
        ).exists()

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
    

# ═══════════════════════════════════════════════════════════
# REPOSITÓRIO DE GRADE HORÁRIA
# ═══════════════════════════════════════════════════════════

class GradeHorariaRepository:
    """
    Repositório para operações com Grade Horária.
    """
    
    @staticmethod
    def get_by_id(grade_id: int, profissional_id: int) -> Optional[GradeHoraria]:
        """Busca grade por ID."""
        try:
            return GradeHoraria.objects.get(id=grade_id, profissional_id=profissional_id)
        except GradeHoraria.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id_or_raise(grade_id: int, profissional_id: int) -> GradeHoraria:
        """Busca grade por ID ou lança exceção."""
        grade = GradeHorariaRepository.get_by_id(grade_id, profissional_id)
        if not grade:
            raise GradeHorariaNotFoundException(grade_id, profissional_id)
        return grade
    
    @staticmethod
    def get_by_profissional_and_dia(
        profissional_id: int,
        dia_semana: int
    ) -> Optional[GradeHoraria]:
        """Busca grade por profissional e dia da semana."""
        try:
            return GradeHoraria.objects.get(
                profissional_id=profissional_id,
                dia_semana=dia_semana
            )
        except GradeHoraria.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_by_profissional(
        profissional_id: int,
        ativo_only: bool = True
    ) -> List[GradeHoraria]:
        """Lista todas as grades de um profissional."""
        queryset = GradeHoraria.objects.filter(profissional_id=profissional_id)
        if ativo_only:
            queryset = queryset.filter(ativo=True)
        return list(queryset.order_by('dia_semana'))
    
    @staticmethod
    def exists_by_profissional_and_dia(
        profissional_id: int,
        dia_semana: int
    ) -> bool:
        """Verifica se já existe grade para este dia."""
        return GradeHoraria.objects.filter(
            profissional_id=profissional_id,
            dia_semana=dia_semana
        ).exists()
    
    @staticmethod
    def create(
        dto: GradeHorariaCreateDTO,
        profissional_id: int,
        criado_por: Optional[UUID] = None
    ) -> GradeHoraria:
        """Cria nova grade horária."""
        with transaction.atomic():
            # Verifica se já existe grade para este dia
            if GradeHorariaRepository.exists_by_profissional_and_dia(
                profissional_id, dto.dia_semana
            ):
                raise GradeHorariaConflictException(profissional_id, dto.dia_semana)
            
            grade = GradeHoraria.objects.create(
                profissional_id=profissional_id,
                dia_semana=dto.dia_semana,
                hora_inicio=dto.hora_inicio,
                hora_fim=dto.hora_fim,
                intervalo_inicio=dto.intervalo_inicio,
                intervalo_fim=dto.intervalo_fim,
                ativo=dto.ativo,
            )
            return grade
    
    @staticmethod
    def update(
        grade: GradeHoraria,
        dto: GradeHorariaUpdateDTO,
        atualizado_por: Optional[UUID] = None
    ) -> GradeHoraria:
        """Atualiza grade existente."""
        update_fields = []
        
        if dto.hora_inicio is not None:
            grade.hora_inicio = dto.hora_inicio
            update_fields.append('hora_inicio')
        if dto.hora_fim is not None:
            grade.hora_fim = dto.hora_fim
            update_fields.append('hora_fim')
        if dto.intervalo_inicio is not None:
            grade.intervalo_inicio = dto.intervalo_inicio
            update_fields.append('intervalo_inicio')
        if dto.intervalo_fim is not None:
            grade.intervalo_fim = dto.intervalo_fim
            update_fields.append('intervalo_fim')
        if dto.ativo is not None:
            grade.ativo = dto.ativo
            update_fields.append('ativo')
        
        if update_fields:
            grade.save(update_fields=update_fields)
        
        return grade


# ═══════════════════════════════════════════════════════════
# REPOSITÓRIO DE DIA INDISPONÍVEL
# ═══════════════════════════════════════════════════════════

class DiaIndisponivelRepository:
    """
    Repositório para operações com Dias Indisponíveis.
    """
    
    @staticmethod
    def get_by_id(dia_id: int, profissional_id: int) -> Optional[DiaIndisponivel]:
        """Busca dia indisponível por ID."""
        try:
            return DiaIndisponivel.objects.get(id=dia_id, profissional_id=profissional_id)
        except DiaIndisponivel.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id_or_raise(dia_id: int, profissional_id: int) -> DiaIndisponivel:
        """Busca dia indisponível por ID ou lança exceção."""
        dia = DiaIndisponivelRepository.get_by_id(dia_id, profissional_id)
        if not dia:
            raise DiaIndisponivelNotFoundException(dia_id, profissional_id)
        return dia
    
    @staticmethod
    def get_all_by_profissional(
        profissional_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None
    ) -> List[DiaIndisponivel]:
        """Lista dias indisponíveis de um profissional."""
        queryset = DiaIndisponivel.objects.filter(profissional_id=profissional_id)
        
        if data_inicio:
            queryset = queryset.filter(data__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__lte=data_fim)
        
        return list(queryset.order_by('data'))
    
    @staticmethod
    def exists_by_profissional_and_data(
        profissional_id: int,
        data: date
    ) -> bool:
        """Verifica se já existe dia indisponível nesta data."""
        return DiaIndisponivel.objects.filter(
            profissional_id=profissional_id,
            data=data
        ).exists()
    
    @staticmethod
    def create(
        dto: DiaIndisponivelCreateDTO,
        profissional_id: int,
        criado_por: Optional[UUID] = None
    ) -> DiaIndisponivel:
        """Cria novo dia indisponível."""
        with transaction.atomic():
            # Verifica se já existe dia indisponível nesta data
            if DiaIndisponivelRepository.exists_by_profissional_and_data(
                profissional_id, dto.data
            ):
                raise DiaIndisponivelConflictException(profissional_id, str(dto.data))
            
            dia = DiaIndisponivel.objects.create(
                profissional_id=profissional_id,
                data=dto.data,
                motivo=dto.motivo,
                criado_por_id=criado_por,
            )
            return dia
    
    @staticmethod
    def delete(dia: DiaIndisponivel) -> None:
        """Deleta dia indisponível."""
        dia.delete()


# ═══════════════════════════════════════════════════════════
# REPOSITÓRIO DE INTERVALO INDISPONÍVEL
# ═══════════════════════════════════════════════════════════

class IntervaloIndisponivelRepository:
    """
    Repositório para operações com Intervalos Indisponíveis.
    """
    
    @staticmethod
    def get_by_id(intervalo_id: int, profissional_id: int) -> Optional[IntervaloIndisponivel]:
        """Busca intervalo por ID."""
        try:
            return IntervaloIndisponivel.objects.get(
                id=intervalo_id,
                profissional_id=profissional_id
            )
        except IntervaloIndisponivel.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id_or_raise(intervalo_id: int, profissional_id: int) -> IntervaloIndisponivel:
        """Busca intervalo por ID ou lança exceção."""
        intervalo = IntervaloIndisponivelRepository.get_by_id(intervalo_id, profissional_id)
        if not intervalo:
            raise IntervaloIndisponivelNotFoundException(intervalo_id, profissional_id)
        return intervalo
    
    @staticmethod
    def get_all_by_profissional_and_data(
        profissional_id: int,
        data: date
    ) -> List[IntervaloIndisponivel]:
        """Lista intervalos indisponíveis de um profissional em uma data."""
        return list(
            IntervaloIndisponivel.objects.filter(
                profissional_id=profissional_id,
                data=data
            ).order_by('hora_inicio')
        )
    
    @staticmethod
    def has_overlap(
        profissional_id: int,
        data: date,
        hora_inicio: time,
        hora_fim: time,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verifica se há sobreposição com intervalos existentes.
        """
        queryset = IntervaloIndisponivel.objects.filter(
            profissional_id=profissional_id,
            data=data,
            hora_inicio__lt=hora_fim,  # Início do novo < Fim do existente
            hora_fim__gt=hora_inicio   # Fim do novo > Início do existente
        )
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        return queryset.exists()
    
    @staticmethod
    def create(
        dto: IntervaloIndisponivelCreateDTO,
        profissional_id: int,
        criado_por: Optional[UUID] = None
    ) -> IntervaloIndisponivel:
        """Cria novo intervalo indisponível."""
        with transaction.atomic():
            # Verifica sobreposição
            if IntervaloIndisponivelRepository.has_overlap(
                profissional_id, dto.data, dto.hora_inicio, dto.hora_fim
            ):
                raise IntervaloIndisponivelConflictException(profissional_id, str(dto.data))
            
            intervalo = IntervaloIndisponivel.objects.create(
                profissional_id=profissional_id,
                data=dto.data,
                hora_inicio=dto.hora_inicio,
                hora_fim=dto.hora_fim,
                motivo=dto.motivo,
                criado_por_id=criado_por,
            )
            return intervalo
    
    @staticmethod
    def delete(intervalo: IntervaloIndisponivel) -> None:
        """Deleta intervalo indisponível."""
        intervalo.delete()


# ═══════════════════════════════════════════════════════════
# REPOSITÓRIO DE SERVIÇO-PROFISSIONAL (Habilitação)
# ═══════════════════════════════════════════════════════════

class ServicoProfissionalRepository:
    """
    Repositório para operações com vínculo Serviço-Profissional.
    """
    
    @staticmethod
    def get_by_id(vinculo_id: int) -> Optional[ServicoProfissional]:
        """Busca vínculo por ID."""
        try:
            return ServicoProfissional.objects.get(id=vinculo_id)
        except ServicoProfissional.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_servico_and_profissional(
        servico_id: int,
        profissional_id: int
    ) -> Optional[ServicoProfissional]:
        """Busca vínculo por serviço e profissional."""
        try:
            return ServicoProfissional.objects.get(
                servico_id=servico_id,
                profissional_id=profissional_id
            )
        except ServicoProfissional.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_by_servico(servico_id: int) -> List[ServicoProfissional]:
        """Lista todos os profissionais habilitados para um serviço."""
        return list(
            ServicoProfissional.objects.filter(
                servico_id=servico_id,
                habilitado=True
            ).select_related('profissional', 'profissional__usuario')
        )
    
    @staticmethod
    def get_all_by_profissional(profissional_id: int) -> List[ServicoProfissional]:
        """Lista todos os serviços habilitados para um profissional."""
        return list(
            ServicoProfissional.objects.filter(
                profissional_id=profissional_id,
                habilitado=True
            ).select_related('servico')
        )
    
    @staticmethod
    def exists_by_servico_and_profissional(
        servico_id: int,
        profissional_id: int
    ) -> bool:
        """Verifica se já existe vínculo."""
        return ServicoProfissional.objects.filter(
            servico_id=servico_id,
            profissional_id=profissional_id
        ).exists()
    
    @staticmethod
    def create(
        servico_id: int,
        profissional_id: int,
        habilitado: bool = True
    ) -> ServicoProfissional:
        """Cria novo vínculo serviço-profissional."""
        with transaction.atomic():
            # Verifica se já existe vínculo
            if ServicoProfissionalRepository.exists_by_servico_and_profissional(
                servico_id, profissional_id
            ):
                raise ServicoProfissionalConflictException(servico_id, profissional_id)
            
            vinculo = ServicoProfissional.objects.create(
                servico_id=servico_id,
                profissional_id=profissional_id,
                habilitado=habilitado,
            )
            return vinculo
    
    @staticmethod
    def toggle_habilitado(vinculo: ServicoProfissional) -> ServicoProfissional:
        """Alterna status habilitado/desabilitado."""
        vinculo.habilitado = not vinculo.habilitado
        vinculo.save(update_fields=['habilitado'])
        return vinculo
    
    @staticmethod
    def delete(vinculo: ServicoProfissional) -> None:
        """Deleta vínculo."""
        vinculo.delete()


# ═══════════════════════════════════════════════════════════
# REPOSITÓRIO DE CONVITE PROFISSIONAL
# ═══════════════════════════════════════════════════════════

class ConviteProfissionalRepository:
    """
    Repositório para operações com Convites Profissionais.
    """
    
    @staticmethod
    def get_by_token(token: str) -> Optional[ConviteProfissional]:
        """Busca convite por token."""
        try:
            return ConviteProfissional.objects.get(token=token)
        except ConviteProfissional.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_token_or_raise(token: str) -> ConviteProfissional:
        """Busca convite por token ou lança exceção."""
        convite = ConviteProfissionalRepository.get_by_token(token)
        if not convite:
            raise ConviteNotFoundException(token)
        return convite
    
    @staticmethod
    def get_by_id(convite_id: int, barbearia_id: UUID) -> Optional[ConviteProfissional]:
        """Busca convite por ID."""
        try:
            return ConviteProfissional.objects.get(
                id=convite_id,
                barbearia_id=barbearia_id
            )
        except ConviteProfissional.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_by_barbearia(
        barbearia_id: UUID,
        status: Optional[str] = None
    ) -> List[ConviteProfissional]:
        """Lista todos os convites de uma barbearia."""
        queryset = ConviteProfissional.objects.filter(barbearia_id=barbearia_id)
        if status:
            queryset = queryset.filter(status=status)
        return list(queryset.order_by('-data_criacao'))
    
    @staticmethod
    def exists_by_email_na_barbearia(
        email: str,
        barbearia_id: UUID,
        status_pendente: bool = True
    ) -> bool:
        """Verifica se já existe convite para este email nesta barbearia."""
        queryset = ConviteProfissional.objects.filter(
            email__iexact=email,
            barbearia_id=barbearia_id
        )
        if status_pendente:
            queryset = queryset.filter(status=ConviteProfissional.STATUS_PENDENTE)
        return queryset.exists()
    
    @staticmethod
    def create(
        dto: ConviteProfissionalCreateDTO,
        barbearia_id: UUID,
        usuario_id: UUID,
        criado_por: Optional[UUID] = None
    ) -> ConviteProfissional:
        """Cria novo convite profissional."""
        with transaction.atomic():
            convite = ConviteProfissional.objects.create(
                barbearia_id=barbearia_id,
                usuario_id=usuario_id,
                nome_completo=dto.nome_completo,
                email=dto.email,
                cpf=dto.cpf,
                telefone=dto.telefone,
                comissao_percentual=dto.comissao_percentual,
                status=ConviteProfissional.STATUS_PENDENTE,
                criado_por_id=criado_por,
            )
            return convite