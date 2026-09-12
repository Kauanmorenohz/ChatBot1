"""
Configuração central do sistema.

- Firebase Admin SDK: acesso ao Firestore (banco de dados).
- Google Calendar: usa uma Service Account com Domain-Wide Delegation,
  o que permite ao backend criar eventos no calendário de qualquer
  barbeiro (ex: joao@suabarbearia.com) sem que cada um precise logar
  individualmente, desde que o domínio seja Google Workspace.

Antes de rodar, você precisa:
1. Criar um projeto no Firebase e baixar o arquivo de credenciais
   (Service Account JSON) -> salvar como 'firebase-credentials.json'
2. Criar/usar uma Service Account no Google Cloud com acesso à
   Calendar API, ativar "Domain-Wide Delegation" nela, e no Admin
   Console do Workspace autorizar o Client ID dessa Service Account
   para o escopo: https://www.googleapis.com/auth/calendar
   -> salvar o JSON dessa service account como 'google-calendar-credentials.json'
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --------------------------------------------------------------------
# Firebase / Firestore
# --------------------------------------------------------------------
FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json"
)

_firebase_app = firebase_admin.initialize_app(
    credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
)
db = firestore.client()

# Nomes das coleções no Firestore
COLECAO_CLIENTES = "clientes"
COLECAO_BARBEIROS = "barbeiros"
COLECAO_SERVICOS = "servicos"
COLECAO_AGENDAMENTOS = "agendamentos"

# --------------------------------------------------------------------
# Google Calendar (Domain-Wide Delegation)
# --------------------------------------------------------------------
GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CALENDAR_CREDENTIALS_PATH", "google-calendar-credentials.json"
)
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service(email_barbeiro: str):
    """
    Retorna um cliente autenticado da Google Calendar API, "impersonando"
    o e-mail do barbeiro (precisa ser um e-mail do mesmo domínio Workspace
    que autorizou a Service Account).
    """
    credenciais = service_account.Credentials.from_service_account_file(
        GOOGLE_CALENDAR_CREDENTIALS_PATH, scopes=GOOGLE_CALENDAR_SCOPES
    )
    credenciais_delegadas = credenciais.with_subject(email_barbeiro)
    return build("calendar", "v3", credentials=credenciais_delegadas)


# --------------------------------------------------------------------
# Configurações gerais do negócio
# --------------------------------------------------------------------
DURACAO_BLOCO_MINUTOS = 30  # tamanho de cada "bloco" da agenda
FUSO_HORARIO = "America/Sao_Paulo"

NOME_BARBEARIA = "Barbearia Exemplo"
MENSAGEM_APRESENTACAO = (
    f"Olá! Seja bem-vindo(a) à {NOME_BARBEARIA}! 💈\n"
    "Antes de começarmos, pode me dizer seu nome completo?"
)
