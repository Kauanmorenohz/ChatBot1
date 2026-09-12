"""
Integração com Google Calendar.
Cria/cancela eventos diretamente no calendário do e-mail do barbeiro,
usando a Service Account com Domain-Wide Delegation configurada em config.py.
"""

from datetime import datetime

from config import get_calendar_service, FUSO_HORARIO


def criar_evento_no_calendario(
    email_barbeiro: str,
    nome_cliente: str,
    nome_servico: str,
    valor: float,
    data_str: str,  # "YYYY-MM-DD"
    hora_inicio_str: str,  # "HH:MM"
    hora_fim_str: str,  # "HH:MM"
) -> str:
    """
    Cria um evento no Google Calendar do barbeiro e retorna o ID do evento
    (necessário guardar no Firestore para permitir cancelar depois).
    """
    servico_calendar = get_calendar_service(email_barbeiro)

    inicio_iso = f"{data_str}T{hora_inicio_str}:00"
    fim_iso = f"{data_str}T{hora_fim_str}:00"

    evento = {
        "summary": f"{nome_servico} - {nome_cliente}",
        "description": (
            f"Cliente: {nome_cliente}\n"
            f"Serviço: {nome_servico}\n"
            f"Valor: R$ {valor:.2f}"
        ),
        "start": {"dateTime": inicio_iso, "timeZone": FUSO_HORARIO},
        "end": {"dateTime": fim_iso, "timeZone": FUSO_HORARIO},
    }

    evento_criado = (
        servico_calendar.events().insert(calendarId="primary", body=evento).execute()
    )
    return evento_criado["id"]


def cancelar_evento_no_calendario(email_barbeiro: str, google_event_id: str) -> None:
    """Remove o evento do calendário do barbeiro (usado ao cancelar um serviço)."""
    servico_calendar = get_calendar_service(email_barbeiro)
    try:
        servico_calendar.events().delete(
            calendarId="primary", eventId=google_event_id
        ).execute()
    except Exception as erro:
        # Se o evento já não existir mais (ex: apagado manualmente), apenas loga.
        print(f"Aviso: não foi possível cancelar o evento {google_event_id}: {erro}")
