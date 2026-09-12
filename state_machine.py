"""
Máquina de estados da conversa.

Esta é a função principal chamada toda vez que uma mensagem chega do
WhatsApp (via serviço Node com Baileys -> webhook do FastAPI).

process_mensagem(telefone, texto) -> texto da resposta a ser enviada
"""

from datetime import datetime, date, timedelta

import firestore_service as fs
import scheduling
import calendar_service
from config import MENSAGEM_APRESENTACAO
from models import Cliente, Agendamento, EstadoConversa


def process_mensagem(telefone: str, texto: str) -> str:
    texto = texto.strip()
    cliente = fs.obter_ou_criar_cliente(telefone)

    if cliente.estado == EstadoConversa.NOVO.value:
        return _iniciar_cadastro(cliente)

    if cliente.estado == EstadoConversa.AGUARDANDO_NOME.value:
        return _salvar_nome_e_mostrar_menu(cliente, texto)

    if cliente.estado == EstadoConversa.MENU_PRINCIPAL.value:
        return _tratar_menu_principal(cliente, texto)

    if cliente.estado == EstadoConversa.ESCOLHENDO_BARBEIRO.value:
        return _tratar_escolha_barbeiro(cliente, texto)

    if cliente.estado == EstadoConversa.ESCOLHENDO_SERVICO.value:
        return _tratar_escolha_servico(cliente, texto)

    if cliente.estado == EstadoConversa.ESCOLHENDO_DIA.value:
        return _tratar_escolha_dia(cliente, texto)

    if cliente.estado == EstadoConversa.ESCOLHENDO_HORARIO.value:
        return _tratar_escolha_horario(cliente, texto)

    if cliente.estado == EstadoConversa.CANCELANDO_SERVICO.value:
        return _tratar_cancelamento(cliente, texto)

    # fallback: se cair em estado desconhecido, volta pro menu
    return _mostrar_menu_principal(cliente)


# --------------------------------------------------------------------
# Cadastro inicial
# --------------------------------------------------------------------
def _iniciar_cadastro(cliente: Cliente) -> str:
    cliente.estado = EstadoConversa.AGUARDANDO_NOME.value
    fs.salvar_cliente(cliente)
    return MENSAGEM_APRESENTACAO


def _salvar_nome_e_mostrar_menu(cliente: Cliente, texto: str) -> str:
    cliente.nome = texto
    fs.salvar_cliente(cliente)
    return f"Prazer, {cliente.nome}! 😄\n\n" + _mostrar_menu_principal(cliente)


# --------------------------------------------------------------------
# Menu principal
# --------------------------------------------------------------------
def _mostrar_menu_principal(cliente: Cliente) -> str:
    cliente.estado = EstadoConversa.MENU_PRINCIPAL.value
    fs.limpar_selecao_em_andamento(cliente)
    fs.salvar_cliente(cliente)
    return (
        "Como posso te ajudar hoje?\n\n"
        "1 - Marcar Serviço\n"
        "2 - Fazer plano mensal\n"
        "3 - Cancelar Serviço"
    )


def _tratar_menu_principal(cliente: Cliente, texto: str) -> str:
    if texto == "1":
        return _mostrar_lista_barbeiros(cliente)
    if texto == "2":
        # Placeholder: fluxo de plano mensal pode ser detalhado depois
        return "O plano mensal ainda está em construção. Em breve estará disponível! 🙂"
    if texto == "3":
        return _iniciar_cancelamento(cliente)

    return "Não entendi 🤔. Digite 1, 2 ou 3 conforme as opções acima."


# --------------------------------------------------------------------
# Fluxo: Marcar Serviço -> escolher barbeiro
# --------------------------------------------------------------------
def _mostrar_lista_barbeiros(cliente: Cliente) -> str:
    barbeiros = fs.listar_barbeiros()
    if not barbeiros:
        return "No momento não há barbeiros cadastrados. Tente novamente mais tarde."

    cliente.estado = EstadoConversa.ESCOLHENDO_BARBEIRO.value
    fs.salvar_cliente(cliente)

    linhas = ["Escolha o barbeiro:"]
    for indice, barbeiro in enumerate(barbeiros, start=1):
        linhas.append(f"{indice} - {barbeiro.nome}")
    return "\n".join(linhas)


def _tratar_escolha_barbeiro(cliente: Cliente, texto: str) -> str:
    barbeiros = fs.listar_barbeiros()
    escolha = _texto_para_indice(texto, len(barbeiros))
    if escolha is None:
        return "Opção inválida. Digite o número correspondente ao barbeiro."

    barbeiro_selecionado = barbeiros[escolha]
    cliente.barbeiro_id_selecionado = barbeiro_selecionado.id
    fs.salvar_cliente(cliente)
    return _mostrar_lista_servicos(cliente)


# --------------------------------------------------------------------
# Fluxo: escolher serviço
# --------------------------------------------------------------------
def _mostrar_lista_servicos(cliente: Cliente) -> str:
    servicos = fs.listar_servicos()
    cliente.estado = EstadoConversa.ESCOLHENDO_SERVICO.value
    fs.salvar_cliente(cliente)

    linhas = ["Escolha o serviço:"]
    for indice, servico in enumerate(servicos, start=1):
        linhas.append(f"{indice} - {servico.nome} R$ {servico.valor:.2f}")
    return "\n".join(linhas)


def _tratar_escolha_servico(cliente: Cliente, texto: str) -> str:
    servicos = fs.listar_servicos()
    escolha = _texto_para_indice(texto, len(servicos))
    if escolha is None:
        return "Opção inválida. Digite o número correspondente ao serviço."

    servico_selecionado = servicos[escolha]
    cliente.servico_id_selecionado = servico_selecionado.id
    fs.salvar_cliente(cliente)

    cliente.estado = EstadoConversa.ESCOLHENDO_DIA.value
    fs.salvar_cliente(cliente)
    return (
        "Para qual dia você gostaria de agendar?\n"
        "Digite a data no formato DD/MM (ex: 25/09).\n\n"
        "(Aqui é onde o comando de calendário interativo do WhatsApp "
        "seria acionado, para o cliente selecionar a data na tela.)"
    )


# --------------------------------------------------------------------
# Fluxo: escolher dia
# --------------------------------------------------------------------
def _tratar_escolha_dia(cliente: Cliente, texto: str) -> str:
    data_selecionada = _texto_para_data(texto)
    if data_selecionada is None:
        return "Data inválida. Digite no formato DD/MM (ex: 25/09)."

    if data_selecionada < date.today():
        return "Essa data já passou. Digite uma data a partir de hoje."

    cliente.data_selecionada = data_selecionada.isoformat()
    fs.salvar_cliente(cliente)
    return _mostrar_horarios_disponiveis(cliente)


# --------------------------------------------------------------------
# Fluxo: escolher horário (usa o cálculo de blocos)
# --------------------------------------------------------------------
def _mostrar_horarios_disponiveis(cliente: Cliente) -> str:
    barbeiro = fs.obter_barbeiro(cliente.barbeiro_id_selecionado)
    servico = fs.obter_servico(cliente.servico_id_selecionado)
    agendamentos_do_dia = fs.listar_agendamentos_do_dia(
        barbeiro.id, cliente.data_selecionada
    )

    horarios = scheduling.calcular_horarios_disponiveis(
        barbeiro=barbeiro,
        agendamentos_do_dia=agendamentos_do_dia,
        duracao_servico_minutos=servico.duracao_SSminutos,
    )

    if not horarios:
        cliente.estado = EstadoConversa.ESCOLHENDO_DIA.value
        fs.salvar_cliente(cliente)
        return (
            "Não há horários disponíveis nesse dia para o serviço escolhido. "
            "Tente outra data (DD/MM)."
        )

    cliente.estado = EstadoConversa.ESCOLHENDO_HORARIO.value
    fs.salvar_cliente(cliente)

    linhas = ["Horários disponíveis:"]
    for indice, horario in enumerate(horarios, start=1):
        linhas.append(f"{indice} - {horario}")
    return "\n".join(linhas)


def _tratar_escolha_horario(cliente: Cliente, texto: str) -> str:
    barbeiro = fs.obter_barbeiro(cliente.barbeiro_id_selecionado)
    servico = fs.obter_servico(cliente.servico_id_selecionado)
    agendamentos_do_dia = fs.listar_agendamentos_do_dia(
        barbeiro.id, cliente.data_selecionada
    )
    horarios = scheduling.calcular_horarios_disponiveis(
        barbeiro=barbeiro,
        agendamentos_do_dia=agendamentos_do_dia,
        duracao_servico_minutos=servico.duracao_minutos,
    )

    escolha = _texto_para_indice(texto, len(horarios))
    if escolha is None:
        return "Opção inválida. Digite o número do horário desejado."

    hora_inicio = horarios[escolha]
    hora_fim = scheduling.calcular_hora_fim(hora_inicio, servico.duracao_minutos)

    # 1. Salva no Firestore
    agendamento = Agendamento(
        id=None,
        cliente_telefone=cliente.telefone,
        cliente_nome=cliente.nome,
        barbeiro_id=barbeiro.id,
        servico_id=servico.id,
        data=cliente.data_selecionada,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        valor=servico.valor,
        status="confirmado",
    )
    agendamento_id = fs.criar_agendamento(agendamento)

    # 2. Cria evento no Google Calendar do barbeiro
    try:
        google_event_id = calendar_service.criar_evento_no_calendario(
            email_barbeiro=barbeiro.email_google,
            nome_cliente=cliente.nome,
            nome_servico=servico.nome,
            valor=servico.valor,
            data_str=cliente.data_selecionada,
            hora_inicio_str=hora_inicio,
            hora_fim_str=hora_fim,
        )
        fs.db.collection(fs.COLECAO_AGENDAMENTOS).document(agendamento_id).update(
            {"google_event_id": google_event_id}
        )
    except Exception as erro:
        print(f"Aviso: falha ao criar evento no Google Calendar: {erro}")

    data_formatada = datetime.fromisoformat(cliente.data_selecionada).strftime(
        "%d/%m/%Y"
    )
    resposta = (
        "✅ Agendamento confirmado!\n\n"
        f"Barbeiro: {barbeiro.nome}\n"
        f"Serviço: {servico.nome}\n"
        f"Data: {data_formatada}\n"
        f"Horário: {hora_inicio} às {hora_fim}\n"
        f"Valor: R$ {servico.valor:.2f}\n\n"
        "Até lá! 💈"
    )
    return resposta + "\n\n" + _mostrar_menu_principal(cliente)


# --------------------------------------------------------------------
# Fluxo: cancelar serviço
# --------------------------------------------------------------------
def _iniciar_cancelamento(cliente: Cliente) -> str:
    agendamentos = fs.listar_agendamentos_futuros_do_cliente(cliente.telefone)
    if not agendamentos:
        return "Você não possui nenhum agendamento futuro.\n\n" + _mostrar_menu_principal(
            cliente
        )

    cliente.estado = EstadoConversa.CANCELANDO_SERVICO.value
    fs.salvar_cliente(cliente)

    linhas = ["Qual agendamento você deseja cancelar?"]
    for indice, agendamento in enumerate(agendamentos, start=1):
        data_formatada = datetime.fromisoformat(agendamento.data).strftime("%d/%m/%Y")
        linhas.append(
            f"{indice} - {data_formatada} às {agendamento.hora_inicio}"
        )
    return "\n".join(linhas)


def _tratar_cancelamento(cliente: Cliente, texto: str) -> str:
    agendamentos = fs.listar_agendamentos_futuros_do_cliente(cliente.telefone)
    escolha = _texto_para_indice(texto, len(agendamentos))
    if escolha is None:
        return "Opção inválida. Digite o número do agendamento a cancelar."

    agendamento = agendamentos[escolha]
    fs.cancelar_agendamento(agendamento.id)

    if agendamento.google_event_id:
        barbeiro = fs.obter_barbeiro(agendamento.barbeiro_id)
        try:
            calendar_service.cancelar_evento_no_calendario(
                barbeiro.email_google, agendamento.google_event_id
            )
        except Exception as erro:
            print(f"Aviso: falha ao cancelar evento no Google Calendar: {erro}")

    return "Agendamento cancelado com sucesso.\n\n" + _mostrar_menu_principal(cliente)


# --------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------
def _texto_para_indice(texto: str, quantidade_opcoes: int):
    """Converte '2' -> índice 1 (base 0), validando o intervalo."""
    if not texto.isdigit():
        return None
    numero = int(texto)
    if numero < 1 or numero > quantidade_opcoes:
        return None
    return numero - 1


def _texto_para_data(texto: str):
    """Converte 'DD/MM' -> objeto date do ano atual (ou próximo ano, se já passou)."""
    try:
        dia, mes = texto.split("/")
        ano = date.today().year
        data = date(ano, int(mes), int(dia))
        if data < date.today():
            data = date(ano + 1, int(mes), int(dia))
        return data
    except (ValueError, IndexError):
        return None
