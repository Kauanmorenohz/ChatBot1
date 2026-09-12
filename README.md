# Barbearia Bot — Backend Python

Este backend em Python (FastAPI) contém **toda a lógica de negócio** do
sistema: cadastro de clientes, menu, escolha de barbeiro/serviço/dia/horário,
cálculo de horários disponíveis por blocos, gravação no Firestore e
criação de eventos no Google Calendar.

Ele **não se conecta diretamente ao WhatsApp**. Como o Baileys (usado para
a conexão não-oficial com o WhatsApp) é uma biblioteca Node.js, a conexão
com o WhatsApp deve rodar em um serviço Node separado, que troca mensagens
com este backend via HTTP. Veja o esqueleto do lado Node mais abaixo.

## 1. Configuração

### 1.1 Firebase
1. Crie um projeto em https://console.firebase.google.com
2. Ative o Firestore.
3. Em "Configurações do projeto" > "Contas de serviço", gere uma chave
   privada e salve o arquivo como `firebase-credentials.json` na raiz
   deste projeto.

### 1.2 Google Calendar (Domain-Wide Delegation)
1. No Google Cloud Console, crie uma Service Account no mesmo projeto
   (ou em outro) e ative a "Google Calendar API".
2. Gere uma chave JSON dessa Service Account e salve como
   `google-calendar-credentials.json`.
3. Na tela de detalhes da Service Account, ative "Enable Google Workspace
   Domain-wide Delegation" e copie o **Client ID** gerado.
4. No Admin Console do Google Workspace (admin.google.com) > Segurança >
   Controles de API > Delegação em todo o domínio, adicione esse Client ID
   autorizando o escopo:
   `https://www.googleapis.com/auth/calendar`

### 1.3 Variáveis de ambiente (opcional)
```
export FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
export GOOGLE_CALENDAR_CREDENTIALS_PATH=google-calendar-credentials.json
```

### 1.4 Instalar dependências e rodar
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 2. Populando o Firestore (dados iniciais)

Antes de testar, cadastre manualmente (pelo console do Firebase, ou um
script simples) pelo menos um barbeiro e alguns serviços:

**Coleção `barbeiros`** (documento com ID livre, ex: `barbeiro1`):
```json
{
  "nome": "João",
  "email_google": "joao@suabarbearia.com",
  "hora_inicio": "10:00",
  "hora_fim": "18:00",
  "dias_trabalho": [0, 1, 2, 3, 4, 5]
}
```

**Coleção `servicos`** (documento com ID livre, ex: `servico1`):
```json
{ "nome": "Barba", "valor": 25.0, "duracao_minutos": 30 }
```
```json
{ "nome": "Cabelo e Barba", "valor": 60.0, "duracao_minutos": 60 }
```
```json
{ "nome": "Sobrancelha", "valor": 20.0, "duracao_minutos": 15 }
```
```json
{ "nome": "Pintar cabelo", "valor": 50.0, "duracao_minutos": 60 }
```
```json
{ "nome": "Pintar barba", "valor": 40.0, "duracao_minutos": 45 }
```
```json
{ "nome": "Pintar cabelo e barba", "valor": 80.0, "duracao_minutos": 90 }
```

## 3. Testando sem o WhatsApp ainda

Você já pode simular o fluxo inteiro só com o backend rodando:
```bash
curl -X POST http://localhost:8000/webhook/mensagem \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511999999999", "mensagem": "oi"}'
```
Isso vai disparar a mensagem de apresentação. Continue mandando requisições
trocando o campo `mensagem` pelas respostas (nome, depois "1" pro menu, etc.)
para simular a conversa completa.

## 4. Esqueleto do serviço Node.js (Baileys) — lado WhatsApp

Este é o serviço que efetivamente conecta ao WhatsApp e repassa as
mensagens para o backend Python acima.

```
whatsapp-service/
  index.js
  package.json
```

`package.json`:
```json
{
  "name": "whatsapp-service",
  "version": "1.0.0",
  "type": "commonjs",
  "dependencies": {
    "@whiskeysockets/baileys": "^6.7.9",
    "axios": "^1.7.7",
    "qrcode-terminal": "^0.12.0"
  }
}
```

`index.js`:
```javascript
const { default: makeWASocket, useMultiFileAuthState } = require("@whiskeysockets/baileys");
const qrcode = require("qrcode-terminal");
const axios = require("axios");

const BACKEND_URL = "http://localhost:8000/webhook/mensagem";

async function iniciar() {
  const { state, saveCreds } = await useMultiFileAuthState("auth_info");

  const sock = makeWASocket({ auth: state });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { qr, connection } = update;
    if (qr) qrcode.generate(qr, { small: true });
    if (connection === "open") console.log("Conectado ao WhatsApp!");
  });

  sock.ev.on("messages.upsert", async ({ messages }) => {
    const msg = messages[0];
    if (!msg.message || msg.key.fromMe) return;

    const telefone = msg.key.remoteJid.replace("@s.whatsapp.net", "");
    const texto =
      msg.message.conversation ||
      msg.message.extendedTextMessage?.text ||
      "";

    if (!texto) return;

    try {
      const resposta = await axios.post(BACKEND_URL, {
        telefone: telefone,
        mensagem: texto,
      });
      await sock.sendMessage(msg.key.remoteJid, { text: resposta.data.resposta });
    } catch (erro) {
      console.error("Erro ao processar mensagem:", erro.message);
    }
  });
}

iniciar();
```

Ao rodar `node index.js` pela primeira vez, um QR code aparece no terminal
— escaneie com o WhatsApp do número que será o bot. As credenciais ficam
salvas em `auth_info/`, então nas próximas execuções não precisa escanear de novo.

## 5. Estrutura de pastas deste backend

```
barbearia_bot/
  config.py            # Firebase + Google Calendar
  models.py             # Estruturas de dados
  firestore_service.py  # Acesso ao banco (CRUD)
  scheduling.py          # Cálculo de horários por blocos
  calendar_service.py    # Criação/cancelamento de eventos no Google Calendar
  state_machine.py       # Máquina de estados da conversa
  main.py                # API que recebe mensagens do serviço Node
  requirements.txt
```

## 6. Próximos passos sugeridos
- Adicionar validação de `dias_trabalho` do barbeiro (hoje o cálculo de
  horários não verifica se o dia escolhido é um dia que ele trabalha).
- Implementar o fluxo de "plano mensal" (hoje é um placeholder).
- Adicionar um comando para o cliente digitar "menu" a qualquer momento e
  voltar ao início.
- Trocar as mensagens numeradas por *Interactive List Messages* se decidir
  migrar para a API oficial do WhatsApp no futuro.
