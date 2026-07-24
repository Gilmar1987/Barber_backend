# apps/agenda/repository.py
from datetime import date
from typing import Dict, List
from apps.agenda.models import Agendamento
from apps.operacional.models import (
    GradeHoraria, 
    DiaIndisponivel, 
    IntervaloIndisponivel, 
    Servico, 
    ServicoProfissional,
    Profissional
)
from django.db import transaction, IntegrityError
from apps.tenants.models import Barbearia
from common.exceptions import ConflitoDeHorarioException
from typing import Optional, Tuple
from datetime import time
from uuid import UUID

class DisponibilidadeRepository:
    """
    Repository para consultas de disponibilidade.
    Segue rigorosamente as Regras 3 e 4 do Guia de Boas Práticas.
    """
    
    @staticmethod
    def get_dados_base(profissional_id: int, servico_id: int) -> Dict:
        """
        Busca duração do serviço e configurações da barbearia.
        ✅ Regra 4: values() para APIs/Serialização leve
        """
        # Busca duração do serviço
        servico = Servico.objects.values('duracao_minutos').get(id=servico_id)
        
        # Busca ID da barbearia do profissional
        prof = Profissional.objects.values('barbearia_id').get(id=profissional_id)
        
        # Busca configurações da barbearia (buffer e balanceamento)
        barbearia = Barbearia.objects.values(
            'buffer_minutos', 
            'balanceamento_minutos'
        ).get(id=prof['barbearia_id'])
        
        return {
            'duracao_minutos': servico['duracao_minutos'],
            'buffer_minutos': barbearia['buffer_minutos'],
            'balanceamento_minutos': barbearia['balanceamento_minutos']
        }

    @staticmethod
    def get_grade_horaria(profissional_id: int, dias_semana: List[int]) -> List[Dict]:
        """
        Busca grades horárias para os dias da semana especificados.
        ✅ Regra 3: Traz apenas os campos necessários
        """
        return list(GradeHoraria.objects.filter(
            profissional_id=profissional_id,
            dia_semana__in=dias_semana,
            ativo=True
        ).values(
            'dia_semana', 
            'hora_inicio', 
            'hora_fim', 
            'intervalo_inicio', 
            'intervalo_fim'
        ))

    @staticmethod
    def get_indisponibilidades(
        profissional_id: int, 
        data_inicio: date, 
        data_fim: date
    ) -> Dict[str, List]:
        """
        Busca dias e intervalos indisponíveis no período.
        ✅ Regra 3: values() e values_list() para performance
        """
        # Dias totalmente bloqueados (folgas)
        dias_bloqueados = list(DiaIndisponivel.objects.filter(
            profissional_id=profissional_id,
            data__range=[data_inicio, data_fim]
        ).values_list('data', flat=True))

        # Intervalos bloqueados dentro de dias de trabalho
        intervalos_bloqueados = list(IntervaloIndisponivel.objects.filter(
            profissional_id=profissional_id,
            data__range=[data_inicio, data_fim]
        ).values('data', 'hora_inicio', 'hora_fim'))

        # Agrupa intervalos por data para facilitar lookup no Service
        intervalos_por_data = {}
        for item in intervalos_bloqueados:
            data_str = item['data'].isoformat()
            if data_str not in intervalos_por_data:
                intervalos_por_data[data_str] = []
            intervalos_por_data[data_str].append({
                'inicio': item['hora_inicio'],
                'fim': item['hora_fim']
            })

        return {
            'dias_bloqueados': dias_bloqueados,
            'intervalos_por_data': intervalos_por_data
        }

    @staticmethod
    def get_agendamentos(
        profissional_id: int, 
        data_inicio: date, 
        data_fim: date
    ) -> Dict[str, List]:
        """
        Busca agendamentos confirmados no período.
        ✅ Regra 1: Evitar N+1 (não há FK sendo acessada em loop)
        """
        # Nota: Assumindo que o model Agendamento existe em apps.agenda.models
        # Se não existir ainda, crie um model básico ou comente esta seção temporariamente
        try:
            from apps.agenda.models import Agendamento
            
            agendamentos = Agendamento.objects.filter(
                profissional_id=profissional_id,
                data__range=[data_inicio, data_fim],
                status='CONFIRMADO'  # Ajuste conforme seu enum de status
            ).values('data', 'hora_inicio', 'hora_fim')

            agendamentos_por_data = {}
            for ag in agendamentos:
                data_str = ag['data'].isoformat()
                if data_str not in agendamentos_por_data:
                    agendamentos_por_data[data_str] = []
                agendamentos_por_data[data_str].append({
                    'inicio': ag['hora_inicio'],
                    'fim': ag['hora_fim']
                })
                
            return agendamentos_por_data
        except ImportError:
            # Se o model Agendamento ainda não existe, retorna dict vazio
            return {}
        


class AgendamentoRepository:
    """
    Repositório para operações de Agendamento com controle de concorrência.
    """
    
    @staticmethod
    def criar_com_lock(
        barbearia_id: UUID,
        profissional_id: int,
        servico_id: int,
        data: date,
        hora_inicio: time,
        hora_fim: time,
        nome_cliente: str,
        telefone_cliente: str,
        cliente_id: Optional[UUID] = None,
        observacoes: Optional[str] = None
    ) -> Agendamento:
        """
        Cria um agendamento com trava de concorrência (select_for_update).
        """
        with transaction.atomic():
            # 1. TRAVA A LINHA DO PROFISSIONAL. 
            # Qualquer outra transação que tentar ler este profissional com select_for_update 
            # ficará em espera até esta transação terminar (COMMIT ou ROLLBACK).
            try:
                Profissional.objects.select_for_update().get(
                    id=profissional_id, 
                    barbearia_id=barbearia_id,
                    ativo=True
                )
            except Profissional.DoesNotExist:
                raise ConflitoDeHorarioException("Profissional não encontrado ou inativo nesta barbearia.")

            # 2. Verifica colisão de horário (agendamentos PENDENTES ou CONFIRMADOS)
            # Usamos a lógica de sobreposição de intervalos
            conflito = Agendamento.objects.filter(
                profissional_id=profissional_id,
                data=data,
                status__in=['PENDENTE', 'CONFIRMADO']
            ).filter(
                hora_inicio__lt=hora_fim,  # Início do novo < Fim do existente
                hora_fim__gt=hora_inicio   # Fim do novo > Início do existente
            ).exists()

            if conflito:
                raise ConflitoDeHorarioException("Conflito de horário: este slot já está reservado.")

            # 3. Cria o agendamento
            try:
                agendamento = Agendamento.objects.create(
                    barbearia_id=barbearia_id,
                    profissional_id=profissional_id,
                    servico_id=servico_id,
                    cliente_id=cliente_id,
                    nome_cliente=nome_cliente,
                    telefone_cliente=telefone_cliente,
                    data=data,
                    hora_inicio=hora_inicio,
                    hora_fim=hora_fim,
                    observacoes=observacoes,
                    status='PENDENTE'
                )
                return agendamento
            except IntegrityError:
                # Fallback de segurança caso o UniqueConstraint do banco seja acionado
                raise ConflitoDeHorarioException("Conflito de horário detectado pelo banco de dados.")
            

    
    @staticmethod
    def get_by_cliente(cliente_id: UUID) -> List[Agendamento]:
        """
        Lista todos os agendamentos de um cliente específico.
        
        ✅ Regra 1 (ConsultasSql): Usa select_related para evitar N+1 queries.
        ✅ Segurança: Filtra estritamente pelo cliente_id do usuário logado.
        """
        return list(
            Agendamento.objects.filter(
                cliente_id=cliente_id,
                barbearia__is_deleted=False  # Segurança extra: não mostra barbearias deletadas
            )
            .select_related(
                'barbearia', 
                'profissional__usuario', 
                'servico'
            )
            .order_by('-data', '-hora_inicio') # Mais recentes primeiro
        )
    
    @staticmethod

    def delete_by_agendamento(cliente_id: UUID) -> None:
        """
        Excl todos os agendamentos de um cliente específico.
        """
        Agendamento.objects.filter(cliente_id=cliente_id).delete()