from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import requests
import sqlite3
import os
import base64
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tocareca2024')

@app.before_request
def criar_tabelas():
    init_db()

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8615854837:AAEkdIWSM837Z5QnA6iOOmguTitW8aQtiWU')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-4991426868')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

SETORES = {
    'cozinha':  {'nome': 'Cozinha',          'emoji': '🍳'},
    'salao':    {'nome': 'Salão/Garçons',     'emoji': '🍽️'},
    'bar':      {'nome': 'Bar',               'emoji': '🍹'},
    'caixa':    {'nome': 'Caixa',             'emoji': '💰'},
    'limpeza':  {'nome': 'Limpeza/Higiene',   'emoji': '🧹'},
    'estoque':  {'nome': 'Estoque/Delivery',  'emoji': '📦'},
}

CHECKLISTS = {
    'cozinha': {
        'Abertura':   ['Ligar equipamentos e checar temperatura','Higienizar bancadas e superfícies','Verificar validade dos ingredientes','Organizar mise en place','Checar extintores e saídas de emergência'],
        'Almoço':     ['Repor insumos da linha de produção','Checar temperatura do buffet (mín 60°C)','Manter organização da praça','Verificar descarte correto de resíduos'],
        'Fechamento': ['Desligar equipamentos e fogões','Limpar e sanitizar toda a cozinha','Armazenar corretamente os alimentos','Verificar lixeiras e descarte'],
    },
    'salao': {
        'Abertura':   ['Organizar mesas e cadeiras','Checar copos e talheres limpos','Preencher cardápios','Verificar ar-condicionado e ventilação'],
        'Almoço':     ['Repor kits de mesa','Limpar mesas após cada atendimento','Checar banheiros a cada 30 min'],
        'Fechamento': ['Recolher toalhas e guardanapos','Limpar cadeiras e mesas','Guardar equipamentos'],
    },
    'bar': {
        'Abertura':   ['Checar estoque de bebidas','Limpar bancada do bar','Verificar gelo e refrigeração','Organizar copos e acessórios'],
        'Almoço':     ['Repor bebidas consumidas','Manter bancada organizada'],
        'Fechamento': ['Fechar garrafas e armazenar','Limpar e higienizar o bar','Desligar equipamentos'],
    },
    'caixa': {
        'Abertura':   ['Conferir fundo de caixa','Testar impressora de cupom','Checar sistema de PDV','Verificar troco disponível'],
        'Almoço':     ['Conferir fechamento parcial','Checar relatório de vendas'],
        'Fechamento': ['Fechar caixa e conferir valores','Gerar relatório do dia','Guardar dinheiro em segurança'],
    },
    'limpeza': {
        'Abertura':   ['Checar estoque de produtos de limpeza','Limpar entrada e calçada','Higienizar banheiros','Trocar sacos de lixo'],
        'Almoço':     ['Checar banheiros a cada hora','Recolher lixo do salão','Varrer e passar pano no salão'],
        'Fechamento': ['Limpeza geral do restaurante','Higienizar banheiros','Descartar todo o lixo','Guardar materiais de limpeza'],
    },
    'estoque': {
        'Abertura':   ['Checar pedidos do dia','Organizar recebimento de mercadorias','Conferir temperaturas das câmaras frias','Atualizar planilha de estoque'],
        'Almoço':     ['Registrar saídas do estoque','Checar itens com baixo estoque'],
        'Fechamento': ['Fechar registro do dia','Checar pedidos para o dia seguinte','Trancar estoque e câmaras'],
    },
}

# ── Banco de dados ──────────────────────────────────────────────────────────
def get_db():
    db = sqlite3.connect('tocareca.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            funcao TEXT NOT NULL,
            setor TEXT NOT NULL,
            turno TEXT NOT NULL,
            criado_em TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER,
            funcionario_nome TEXT,
            setor TEXT,
            turno TEXT,
            itens_total INTEGER,
            itens_ok INTEGER,
            score_ia INTEGER DEFAULT 0,
            feedback_ia TEXT DEFAULT '',
            enviado_em TEXT DEFAULT (datetime('now'))
        );
    ''')
    db.commit()
    db.close()

# ── Telegram ────────────────────────────────────────────────────────────────
def enviar_telegram(texto):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': texto})

def notificar_checklist(nome, funcao, setor, turno, feitos, total, score_ia, feedback_ia):
    pct = round((feitos / total) * 100)
    emoji_status = '✅' if pct == 100 else ('⚠️' if pct >= 70 else '🚨')
    emoji_ia = '✅' if score_ia >= 80 else ('⚠️' if score_ia >= 60 else '🚨')
    s = SETORES.get(setor, {})
    hora = datetime.now().strftime('%H:%M')
    msg = (
        f"🍽️ Tô Careca de Saber\n"
        f"{'─'*30}\n"
        f"{s.get('emoji','')} Setor: {s.get('nome', setor)}\n"
        f"👤 Funcionário: {nome} ({funcao})\n"
        f"🕐 Horário: {hora} — Turno: {turno}\n"
        f"{'─'*30}\n"
        f"{emoji_status} Checklist: {feitos}/{total} itens ({pct}%)\n"
        f"{emoji_ia} Foto/IA: {score_ia}% de conformidade\n"
        f"📋 {feedback_ia}\n"
        f"{'─'*30}\n"
        f"{'🟢 TUDO OK!' if pct==100 and score_ia>=80 else '🔴 REQUER ATENÇÃO!' if pct<70 or score_ia<60 else '🟡 ATENÇÃO PARCIAL'}"
    )
    enviar_telegram(msg)

# ── IA — análise de foto ────────────────────────────────────────────────────
def analisar_foto_ia(base64_img, setor):
    if not ANTHROPIC_API_KEY:
        return 75, 'IA não configurada. Configure ANTHROPIC_API_KEY para análise real.'
    try:
        headers = {
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        prompt = (
            f"Você é um inspetor de qualidade de restaurantes. "
            f"Analise esta foto do setor de {SETORES.get(setor,{}).get('nome',setor)} "
            f"e responda APENAS em JSON: {{\"score\": <0-100>, \"feedback\": \"<frase curta>\", \"aprovado\": <true/false>}}. "
            f"Considere: organização, limpeza, disposição dos itens, conformidade com padrões de higiene."
        )
        body = {
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 200,
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': base64_img}},
                    {'type': 'text', 'text': prompt}
                ]
            }]
        }
        r = requests.post('https://api.anthropic.com/v1/messages', headers=headers, json=body, timeout=30)
        data = r.json()
        text = data['content'][0]['text']
        clean = text.replace('```json','').replace('```','').strip()
        result = json.loads(clean)
        return result.get('score', 70), result.get('feedback', 'Análise concluída.')
    except Exception as e:
        return 70, f'Erro na análise: {str(e)}'

# ── Rotas ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('painel'))

@app.route('/painel')
def painel():
    if not session.get('logado'):
        return redirect(url_for('login'))
    db = get_db()
    funcs = db.execute('SELECT * FROM funcionarios ORDER BY setor').fetchall()
    checks = db.execute('SELECT * FROM checklists ORDER BY enviado_em DESC LIMIT 20').fetchall()
    db.close()
    return render_template('painel.html', funcionarios=funcs, checklists=checks, setores=SETORES)

@app.route('/login', methods=['GET','POST'])
def login():
    erro = ''
    if request.method == 'POST':
        senha = request.form.get('senha','')
        if senha == os.environ.get('SENHA_ADMIN', 'tocareca123'):
            session['logado'] = True
            return redirect(url_for('painel'))
        erro = 'Senha incorreta.'
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/funcionarios', methods=['GET','POST'])
def funcionarios():
    if not session.get('logado'):
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        db.execute('INSERT INTO funcionarios (nome,funcao,setor,turno) VALUES (?,?,?,?)',
                   (request.form['nome'], request.form['funcao'],
                    request.form['setor'], request.form['turno']))
        db.commit()
    funcs = db.execute('SELECT * FROM funcionarios ORDER BY setor, nome').fetchall()
    db.close()
    return render_template('funcionarios.html', funcionarios=funcs, setores=SETORES)

@app.route('/funcionarios/deletar/<int:fid>')
def deletar_funcionario(fid):
    if not session.get('logado'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM funcionarios WHERE id=?', (fid,))
    db.commit()
    db.close()
    return redirect(url_for('funcionarios'))

@app.route('/checklist/<setor>')
def checklist(setor):
    if setor not in SETORES:
        return 'Setor não encontrado.', 404
    turno = request.args.get('turno', 'Abertura')
    itens = CHECKLISTS.get(setor, {}).get(turno, [])
    db = get_db()
    funcs = db.execute('SELECT * FROM funcionarios WHERE setor=?', (setor,)).fetchall()
    db.close()
    return render_template('checklist.html', setor=setor, info=SETORES[setor],
                           turno=turno, itens=itens, funcionarios=funcs,
                           turnos=['Abertura','Almoço','Tarde','Jantar','Fechamento'])

@app.route('/checklist/<setor>/enviar', methods=['POST'])
def enviar_checklist(setor):
    funcionario_id = request.form.get('funcionario_id', '')
    funcionario_nome = request.form.get('funcionario_nome', 'Funcionário')
    funcao = request.form.get('funcao', '')
    turno = request.form.get('turno', 'Abertura')
    itens = CHECKLISTS.get(setor, {}).get(turno, [])
    feitos = sum(1 for i in range(len(itens)) if request.form.get(f'item_{i}'))
    score_ia = 0
    feedback_ia = 'Sem foto enviada.'

    foto = request.files.get('foto')
    if foto and foto.filename:
        img_bytes = foto.read()
        b64 = base64.b64encode(img_bytes).decode()
        score_ia, feedback_ia = analisar_foto_ia(b64, setor)

    db = get_db()
    db.execute('INSERT INTO checklists (funcionario_id,funcionario_nome,setor,turno,itens_total,itens_ok,score_ia,feedback_ia) VALUES (?,?,?,?,?,?,?,?)',
               (funcionario_id, funcionario_nome, setor, turno, len(itens), feitos, score_ia, feedback_ia))
    db.commit()
    db.close()

    notificar_checklist(funcionario_nome, funcao, setor, turno, feitos, len(itens), score_ia, feedback_ia)
    return render_template('confirmacao.html', nome=funcionario_nome, setor=SETORES[setor],
                           feitos=feitos, total=len(itens), score_ia=score_ia, feedback_ia=feedback_ia)

@app.route('/api/stats')
def api_stats():
    if not session.get('logado'):
        return jsonify({'erro': 'não autorizado'}), 401
    db = get_db()
    total_funcs = db.execute('SELECT COUNT(*) FROM funcionarios').fetchone()[0]
    total_checks = db.execute('SELECT COUNT(*) FROM checklists').fetchone()[0]
    media_ia = db.execute('SELECT AVG(score_ia) FROM checklists WHERE score_ia > 0').fetchone()[0] or 0
    db.close()
    return jsonify({'funcionarios': total_funcs, 'checklists': total_checks, 'media_ia': round(media_ia)})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
