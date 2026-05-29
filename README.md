# 🍽️ Tô Careca de Saber — Sistema de Checklist

## O que é esse sistema?
Sistema completo de checklist para restaurante com:
- ✅ Painel do dono/gerente com senha
- 👤 Cadastro de funcionários por setor
- 📋 Checklist por setor e turno (link exclusivo para cada área)
- 📸 Análise de fotos pela IA (Claude Vision)
- 📲 Notificações em tempo real no Telegram

---

## Como colocar no ar (Railway — GRATUITO)

### Passo 1 — Criar conta no GitHub
1. Acesse https://github.com e crie uma conta gratuita
2. Crie um novo repositório chamado `tocareca-checklist`
3. Faça upload de todos os arquivos desta pasta

### Passo 2 — Criar conta no Railway
1. Acesse https://railway.app
2. Clique em "Start a New Project"
3. Escolha "Deploy from GitHub repo"
4. Selecione o repositório `tocareca-checklist`

### Passo 3 — Configurar variáveis de ambiente
No Railway, vá em **Settings → Variables** e adicione:

```
TELEGRAM_TOKEN=8615854837:AAEkdIWSM837Z5QnA6iOOmguTitW8aQtiWU
TELEGRAM_CHAT_ID=-4991426868
SENHA_ADMIN=tocareca123
SECRET_KEY=umasenhasecretaaleatoria123
ANTHROPIC_API_KEY=sk-ant-... (opcional, para análise de fotos por IA)
```

### Passo 4 — Deploy automático
O Railway faz o deploy automaticamente. Em ~2 minutos você terá uma URL como:
`https://tocareca-checklist.up.railway.app`

---

## Como usar

### Dono / Gerente
- Acesse a URL do sistema e faça login com a senha definida em `SENHA_ADMIN`
- Cadastre os funcionários em **Funcionários**
- Compartilhe os links de cada setor com os funcionários

### Funcionários
Cada setor tem um link único:
- Cozinha: `/checklist/cozinha`
- Salão: `/checklist/salao`
- Bar: `/checklist/bar`
- Caixa: `/checklist/caixa`
- Limpeza: `/checklist/limpeza`
- Estoque: `/checklist/estoque`

O funcionário acessa o link, seleciona o nome, marca os itens, tira a foto e envia.

### Telegram
Você e a gerente recebem notificação assim:
```
🍽️ Tô Careca de Saber
──────────────────────
🍳 Setor: Cozinha
👤 Funcionário: João Silva (Cozinheiro)
🕐 Horário: 08:15 — Turno: Abertura
──────────────────────
✅ Checklist: 5/5 itens (100%)
✅ Foto/IA: 91% de conformidade
📋 Área organizada e dentro do padrão.
──────────────────────
🟢 TUDO OK!
```

---

## Análise de fotos por IA (opcional)
Para ativar a análise real de fotos:
1. Acesse https://console.anthropic.com
2. Crie uma chave de API
3. Adicione como variável `ANTHROPIC_API_KEY` no Railway

Sem a chave, o sistema funciona normalmente mas com score fixo de 75%.

---

## Arquivos do projeto
```
tocareca/
├── app.py              ← servidor principal
├── requirements.txt    ← dependências Python
├── Procfile            ← configuração Railway
├── templates/
│   ├── base.html       ← layout base
│   ├── login.html      ← tela de login
│   ├── painel.html     ← painel do dono
│   ├── funcionarios.html ← cadastro de funcionários
│   ├── checklist.html  ← checklist do funcionário
│   └── confirmacao.html ← tela após envio
```
