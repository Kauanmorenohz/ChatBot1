"""
Camada de acesso ao Firestore.
Todas as leituras/escritas no banco de dados passam por aqui.
"""

from typing import Optional, List
from datetime import date

from config import (
    db,
    COLECAO_CLIENTES,
    COLECAO_BARBEIROS,
    COLECAO_SERVICOS,
    COLECAO_AGENDAMENTOS,
)
from models import Cliente, Barbeiro, Servico, Agendamento, EstadoConversa


# --------------------------------------------------------------------
# CLIENTES
# --------------------------------------------------------------------
def obter_cliente(telefone: str) -> Optional[Cliente]:
    doc = db.collection(COLECAO_CLIENTES).document(telefone).get()
    if not doc.exists:
        return None
    dados = doc.to_dict()
    return Cliente(telefone=telefone, **dados)


def obter_ou_criar_cliente(telefone: str) -> Cliente:
    """
    Verifica se é a primeira mensagem daquele número.
    Se não existir, cria o registro com estado inicial 'novo'.
    """
    cliente = obter_cliente(telefone)
    if cliente is not None:
        return cliente

    cliente = Cliente(telefone=telefone, estado=EstadoConversa.NOVO.value)
    salvar_cliente(cliente)
    return cliente


def salvar_cliente(cliente: Cliente) -> None:
    dados = {
        "nome": cliente.nome,
        "estado": cliente.estado,
        "barbeiro_id_selecionado": cliente.barbeiro_id_selecionado,
        "servico_id_selecionado": cliente.servico_id_selecionado,
        "data_selecionada": cliente.data_selecionada,
    }
    db.collection(COLECAO_CLIENTES).document(cliente.telefone).set(dados)


def limpar_selecao_em_andamento(cliente: Cliente) -> None:
    """Reseta as escolhas temporárias (usado ao voltar ao menu principal)."""
    cliente.barbeiro_id_selecionado = None
    cliente.servico_id_selecionado = None
    cliente.data_selecionada = None


# --------------------------------------------------------------------
# BARBEIROS
# --------------------------------------------------------------------
def listar_barbeiros() -> List[Barbeiro]:
    docs = db.collection(COLECAO_BARBEIROS).stream()
    return [Barbeiro(id=doc.id, **doc.to_dict()) for doc in docs]


def obter_barbeiro(barbeiro_id: str) -> Optional[Barbeiro]:
    doc = db.collection(COLECAO_BARBEIROS).document(barbeiro_id).get()
    if not doc.exists:
        return None
    return Barbeiro(id=doc.id, **doc.to_dict())


# --------------------------------------------------------------------
# SERVIÇOS
# --------------------------------------------------------------------
def listar_servicos() -> List[Servico]:
    docs = db.collection(COLECAO_SERVICOS).stream()
    return [Servico(id=doc.id, **doc.to_dict()) for doc in docs]


def obter_servico(servico_id: str) -> Optional[Servico]:
    doc = db.collection(COLECAO_SERVICOS).document(servico_id).get()
    if not doc.exists:
        return None
    return Servico(id=doc.id, **doc.to_dict())


# --------------------------------------------------------------------
# AGENDAMENTOS
# --------------------------------------------------------------------
def listar_agendamentos_do_dia(barbeiro_id: str, data_str: str) -> List[Agendamento]:
    """Lista todos os agendamentos ATIVOS (não cancelados) de um barbeiro num dia."""
    query = (
        db.collection(COLECAO_AGENDAMENTOS)
        .where("barbeiro_id", "==", barbeiro_id)
        .where("data", "==", data_str)
        .where("status", "==", "confirmado")
    )
    docs = query.stream()
    return [Agendamento(id=doc.id, **doc.to_dict()) for doc in docs]


def criar_agendamento(agendamento: Agendamento) -> str:
    dados = {
        "cliente_telefone": agendamento.cliente_telefone,
        "cliente_nome": agendamento.cliente_nome,
        "barbeiro_id": agendamento.barbeiro_id,
        "servico_id": agendamento.servico_id,
        "data": agendamento.data,
        "hora_inicio": agendamento.hora_inicio,
        "hora_fim": agendamento.hora_fim,
        "valor": agendamento.valor,
        "status": agendamento.status,
        "google_event_id": agendamento.google_event_id,
    }
    _, doc_ref = db.collection(COLECAO_AGENDAMENTOS).add(dados)
    return doc_ref.id


def listar_agendamentos_futuros_do_cliente(telefone: str) -> List[Agendamento]:
    hoje_str = date.today().isoformat()
    query = (
        db.collection(COLECAO_AGENDAMENTOS)
        .where("cliente_telefone", "==", telefone)
        .where("status", "==", "confirmado")
        .where("data", ">=", hoje_str)
    )
    docs = query.stream()
    return [Agendamento(id=doc.id, **doc.to_dict()) for doc in docs]


def cancelar_agendamento(agendamento_id: str) -> None:
    db.collection(COLECAO_AGENDAMENTOS).document(agendamento_id).update(
        {"status": "cancelado"}
    )
