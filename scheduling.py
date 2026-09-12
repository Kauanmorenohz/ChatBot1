"""
Lógica de cálculo de horários disponíveis.

Regra (conforme definido):
- O expediente do barbeiro é dividido em blocos fixos (padrão 30 min).
- Cada serviço tem uma duração estimada, que é convertida em "quantos
  blocos consecutivos" ele ocupa.
- Um horário só é oferecido ao cliente se houver blocos consecutivos
  livres suficientes para cobrir toda a duração do serviço.
"""

import math
from datetime import date, datetime, time, timedelta
from typing import List

from config import DURACAO_BLOCO_MINUTOS
from models import Barbeiro, Agendamento


def _string_para_hora(hhmm: str) -> time:
    return datetime.strptime(hhmm, "%H:%M").time()


def _hora_para_string(t: time) -> str:
    return t.strftime("%H:%M")


def gerar_blocos_do_expediente(hora_inicio: str, hora_fim: str) -> List[time]:
    """
    Gera a lista de horários de início de cada bloco do expediente.
    Ex: hora_inicio="10:00", hora_fim="18:00", bloco=30min ->
        [10:00, 10:30, 11:00, ..., 17:30]
    (17:30 é o último bloco possível pois termina exatamente às 18:00)
    """
    inicio_dt = datetime.combine(date.today(), _string_para_hora(hora_inicio))
    fim_dt = datetime.combine(date.today(), _string_para_hora(hora_fim))

    blocos = []
    atual = inicio_dt
    while atual + timedelta(minutes=DURACAO_BLOCO_MINUTOS) <= fim_dt:
        blocos.append(atual.time())
        atual += timedelta(minutes=DURACAO_BLOCO_MINUTOS)
    return blocos


def _blocos_ocupados(
    agendamentos_do_dia: List[Agendamento],
) -> set:
    """
    Retorna um set com todos os horários de início de bloco que já
    estão ocupados por algum agendamento existente naquele dia.
    Um agendamento pode ocupar vários blocos (se o serviço dele for
    mais longo que a duração de um bloco).
    """
    ocupados = set()
    for agendamento in agendamentos_do_dia:
        inicio = datetime.combine(date.today(), _string_para_hora(agendamento.hora_inicio))
        fim = datetime.combine(date.today(), _string_para_hora(agendamento.hora_fim))
        atual = inicio
        while atual < fim:
            ocupados.add(atual.time())
            atual += timedelta(minutes=DURACAO_BLOCO_MINUTOS)
    return ocupados


def calcular_horarios_disponiveis(
    barbeiro: Barbeiro,
    agendamentos_do_dia: List[Agendamento],
    duracao_servico_minutos: int,
) -> List[str]:
    """
    Retorna a lista de horários (strings "HH:MM") em que o serviço
    pode COMEÇAR, considerando que ele precisa de N blocos consecutivos
    livres a partir daquele ponto.
    """
    blocos_expediente = gerar_blocos_do_expediente(
        barbeiro.hora_inicio, barbeiro.hora_fim
    )
    ocupados = _blocos_ocupados(agendamentos_do_dia)

    # quantos blocos consecutivos o serviço exige
    blocos_necessarios = math.ceil(duracao_servico_minutos / DURACAO_BLOCO_MINUTOS)

    livres = [b for b in blocos_expediente if b not in ocupados]
    livres_set = set(livres)

    horarios_validos = []

    for indice, bloco_inicial in enumerate(blocos_expediente):
        if bloco_inicial not in livres_set:
            continue  # o próprio bloco inicial já está ocupado

        # verifica se os próximos (blocos_necessarios - 1) blocos também
        # existem no expediente e estão livres (sequência contínua)
        sequencia_ok = True
        dt_cursor = datetime.combine(date.today(), bloco_inicial)

        for passo in range(blocos_necessarios):
            horario_necessario = (
                dt_cursor + timedelta(minutes=DURACAO_BLOCO_MINUTOS * passo)
            ).time()
            if horario_necessario not in livres_set:
                sequencia_ok = False
                break

        if sequencia_ok:
            horarios_validos.append(_hora_para_string(bloco_inicial))

    return horarios_validos


def calcular_hora_fim(hora_inicio_str: str, duracao_minutos: int) -> str:
    """Dado um horário de início e a duração do serviço, calcula o horário de término."""
    inicio_dt = datetime.combine(date.today(), _string_para_hora(hora_inicio_str))
    fim_dt = inicio_dt + timedelta(minutes=duracao_minutos)
    return _hora_para_string(fim_dt.time())
