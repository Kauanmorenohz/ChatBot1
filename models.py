"""
Modelos de dados (estruturas) usados no sistema.
Não é o ORM em si (o Firestore é NoSQL), apenas dataclasses
para deixar o código mais legível e tipado.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import date, time
from typing import Optional


class EstadoConversa(str, Enum):
    """Cada etapa da conversa do cliente com o bot."""
    NOVO = "novo"
    AGUARDANDO_NOME = "aguardando_nome"
    MENU_PRINCIPAL = "menu_principal"
    ESCOLHENDO_BARBEIRO = "escolhendo_barbeiro"
    ESCOLHENDO_SERVICO = "escolhendo_servico"
    ESCOLHENDO_DIA = "escolhendo_dia"
    ESCOLHENDO_HORARIO = "escolhendo_horario"
    AGENDAMENTO_CONFIRMADO = "agendamento_confirmado"
    CANCELANDO_SERVICO = "cancelando_servico"


@dataclass
class Cliente:
    telefone: str  # usado como ID do documento no Firestore
    nome: Optional[str] = None
    estado: str = EstadoConversa.NOVO.value
    # dados temporários da escolha em andamento (vão sendo preenchidos
    # conforme o cliente avança no fluxo de agendamento)
    barbeiro_id_selecionado: Optional[str] = None
    servico_id_selecionado: Optional[str] = None
    data_selecionada: Optional[str] = None  # formato "YYYY-MM-DD"


@dataclass
class Barbeiro:
    id: str
    nome: str
    email_google: str
    hora_inicio: str  # ex: "10:00"
    hora_fim: str  # ex: "18:00"
    dias_trabalho: list = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    # dias_trabalho: 0=segunda ... 6=domingo


@dataclass
class Servico:
    id: str
    nome: str
    valor: float
    duracao_minutos: int


@dataclass
class Agendamento:
    id: Optional[str]
    cliente_telefone: str
    cliente_nome: str
    barbeiro_id: str
    servico_id: str
    data: str  # "YYYY-MM-DD"
    hora_inicio: str  # "HH:MM"
    hora_fim: str  # "HH:MM"
    valor: float
    status: str = "confirmado"  # confirmado | cancelado
    google_event_id: Optional[str] = None
