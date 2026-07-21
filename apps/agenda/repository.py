# apps/agenda/repository.py
from datetime import date
from typing import Dict, List
from apps.operacional.models import (
    GradeHoraria, 
    DiaIndisponivel, 
    IntervaloIndisponivel, 
    Servico, 
    ServicoProfissional,
    Profissional
)
from apps.tenants.models import Barbearia

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