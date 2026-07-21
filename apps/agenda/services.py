# apps/agenda/services.py
import logging
from datetime import date, datetime, time, timedelta
from typing import List
from apps.agenda.dtos import (
    DisponibilidadeSearchDTO, 
    SlotDisponivelDTO, 
    DisponibilidadeResponseDTO
)
from apps.agenda.repository import DisponibilidadeRepository

logger = logging.getLogger(__name__)

class DisponibilidadeService:
    """
    Service para cálculo de disponibilidade de horários.
    Implementa o algoritmo de "Subtração de Timeline".
    """
    
    def __init__(self, repository: DisponibilidadeRepository = None):
        self.repo = repository or DisponibilidadeRepository()

    def calcular_disponibilidade(
        self, 
        dto: DisponibilidadeSearchDTO
    ) -> DisponibilidadeResponseDTO:
        """
        Calcula slots disponíveis para um profissional e serviço em um intervalo de datas.
        """
        try:
            # 1. Dados Base (duração, buffer, balanceamento)
            base = self.repo.get_dados_base(dto.profissional_id, dto.servico_id)
            duracao = base['duracao_minutos']
            buffer = base['buffer_minutos']
            balanceamento = base['balanceamento_minutos']

            # 2. Dados de Restrição (Queries otimizadas com .values)
            dias_semana = [
                (dto.data_inicio + timedelta(days=i)).weekday() 
                for i in range((dto.data_fim - dto.data_inicio).days + 1)
            ]
            grades = self.repo.get_grade_horaria(dto.profissional_id, dias_semana)
            indisponibilidades = self.repo.get_indisponibilidades(
                dto.profissional_id, 
                dto.data_inicio, 
                dto.data_fim
            )
            agendamentos = self.repo.get_agendamentos(
                dto.profissional_id, 
                dto.data_inicio, 
                dto.data_fim
            )

            slots_disponiveis = []
            data_atual = dto.data_inicio

            # 3. Algoritmo de Subtração de Timeline (Dia a Dia)
            while data_atual <= dto.data_fim:
                data_str = data_atual.isoformat()
                dia_semana = data_atual.weekday()

                # Pula se o dia estiver na lista de indisponibilidade total
                if data_atual in indisponibilidades['dias_bloqueados']:
                    data_atual += timedelta(days=1)
                    continue

                # Pula se não houver grade horária para este dia da semana
                grade_do_dia = next(
                    (g for g in grades if g['dia_semana'] == dia_semana), 
                    None
                )
                if not grade_do_dia:
                    data_atual += timedelta(days=1)
                    continue

                # Define blocos de bloqueio para o dia
                blocos_bloqueados = []
                
                # a) Intervalo de almoço da grade
                if grade_do_dia['intervalo_inicio'] and grade_do_dia['intervalo_fim']:
                    blocos_bloqueados.append((
                        grade_do_dia['intervalo_inicio'], 
                        grade_do_dia['intervalo_fim']
                    ))
                
                # b) Intervalos indisponíveis manuais
                for bloco in indisponibilidades['intervalos_por_data'].get(data_str, []):
                    blocos_bloqueados.append((bloco['inicio'], bloco['fim']))
                
                # c) Agendamentos existentes + Buffer (apenas no fim, conforme regra)
                for ag in agendamentos.get(data_str, []):
                    fim_com_buffer = self._somar_minutos(ag['fim'], buffer)
                    blocos_bloqueados.append((ag['inicio'], fim_com_buffer))

                # Ordena blocos bloqueados por horário de início
                blocos_bloqueados.sort(key=lambda x: x[0])

                # Gera slots nos espaços livres
                slots_do_dia = self._gerar_slots(
                    inicio_trabalho=grade_do_dia['hora_inicio'],
                    fim_trabalho=grade_do_dia['hora_fim'],
                    blocos_bloqueados=blocos_bloqueados,
                    duracao=duracao,
                    balanceamento=balanceamento,
                    data=data_atual
                )
                slots_disponiveis.extend(slots_do_dia)
                data_atual += timedelta(days=1)

            logger.info(
                f"Calculada disponibilidade: {len(slots_disponiveis)} slots "
                f"para profissional {dto.profissional_id}"
            )

            return DisponibilidadeResponseDTO(
                success=True,
                data=slots_disponiveis,
                error=None,
                details={'total_slots': len(slots_disponiveis)}
            )

        except Exception as e:
            logger.exception("Erro ao calcular disponibilidade")
            return DisponibilidadeResponseDTO(
                success=False,
                data=[],
                error="Erro interno ao calcular disponibilidade",
                details=None
            )

    def _somar_minutos(self, hora: time, minutos: int) -> time:
        """Helper para somar minutos a um objeto time."""
        dt = datetime.combine(datetime.today(), hora) + timedelta(minutes=minutos)
        return dt.time()

    def _gerar_slots(
        self, 
        inicio_trabalho: time, 
        fim_trabalho: time, 
        blocos_bloqueados: List, 
        duracao: int, 
        balanceamento: int, 
        data: date
    ) -> List[SlotDisponivelDTO]:
        """
        Gera slots disponíveis nos espaços livres entre blocos bloqueados.
        Aplica regra de balanceamento para agendamentos curtos no final do expediente.
        """
        slots = []
        current_time = datetime.combine(datetime.today(), inicio_trabalho)
        fim_trabalho_dt = datetime.combine(datetime.today(), fim_trabalho)

        for bloco_inicio, bloco_fim in blocos_bloqueados:
            bloco_inicio_dt = datetime.combine(datetime.today(), bloco_inicio)
            bloco_fim_dt = datetime.combine(datetime.today(), bloco_fim)

            # Enquanto houver tempo livre antes do próximo bloqueio
            while current_time < bloco_inicio_dt:
                slot_fim_dt = current_time + timedelta(minutes=duracao)

                # Verifica se o slot cabe antes do bloqueio
                if slot_fim_dt <= bloco_inicio_dt:
                    slots.append(SlotDisponivelDTO(
                        data=data, 
                        horario_inicio=current_time.time(), 
                        horario_fim=slot_fim_dt.time()
                    ))
                    current_time += timedelta(minutes=duracao)
                else:
                    # Regra de Balanceamento: Se faltar pouco tempo para o bloqueio
                    diff_minutos = int((bloco_inicio_dt - current_time).total_seconds() / 60)
                    if diff_minutos >= (duracao - balanceamento) and diff_minutos < duracao:
                        slots.append(SlotDisponivelDTO(
                            data=data, 
                            horario_inicio=current_time.time(), 
                            horario_fim=bloco_inicio_dt.time()
                        ))
                    break

            # Avança o current_time para o fim do bloqueio
            if bloco_fim_dt > current_time:
                current_time = bloco_fim_dt

        # Verifica o espaço restante após o último bloqueio até o fim do expediente
        while current_time < fim_trabalho_dt:
            slot_fim_dt = current_time + timedelta(minutes=duracao)

            if slot_fim_dt <= fim_trabalho_dt:
                slots.append(SlotDisponivelDTO(
                    data=data, 
                    horario_inicio=current_time.time(), 
                    horario_fim=slot_fim_dt.time()
                ))
                current_time += timedelta(minutes=duracao)
            else:
                diff_minutos = int((fim_trabalho_dt - current_time).total_seconds() / 60)
                if diff_minutos >= (duracao - balanceamento) and diff_minutos < duracao:
                    slots.append(SlotDisponivelDTO(
                        data=data, 
                        horario_inicio=current_time.time(), 
                        horario_fim=fim_trabalho_dt.time()
                    ))
                break

        return slots