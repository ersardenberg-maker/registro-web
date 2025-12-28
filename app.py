import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

# --- CONFIGURAÇÃO DA APLICAÇÃO ---
app = Flask(__name__)
# Em produção, deve usar uma chave secreta complexa definida nas variáveis de ambiente
app.secret_key = 'chave_secreta_segura_para_sessao_app_final'
bcrypt = Bcrypt(app)

# --- CONFIGURAÇÃO DA BASE DE DADOS ---
# Tenta obter a URL do Render (PostgreSQL). Se não existir, usa SQLite local.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Correção necessária para o SQLAlchemy em alguns sistemas de cloud que usam postgres://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'local_database.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- CONFIGURAÇÃO DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para aceder ao sistema."
login_manager.login_message_category = "info"

# --- MODELOS DE DADOS ---

class Utilizador(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Sessao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_registro = db.Column(db.String(10), nullable=False)
    sessao = db.Column(db.String(100), nullable=False)
    data_sessao = db.Column(db.String(10), nullable=False)
    dirigente = db.Column(db.String(150), nullable=False)
    explanacao = db.Column(db.String(200))
    leitura_documentos = db.Column(db.String(200))
    responsavel_preenchimento = db.Column(db.String(150), nullable=False)
    qtd_pessoas = db.Column(db.Integer, nullable=False)
    # Armazena os lotes como string formatada: "ID_LOTE:QTD|ID_LOTE2:QTD"
    lotes_utilizados = db.Column(db.String(500)) 
    litros_iniciais = db.Column(db.Float, nullable=False)
    litros_finais = db.Column(db.Float, nullable=False)
    litros_consumidos = db.Column(db.Float, nullable=False)
    consumo_por_pessoa_ml = db.Column(db.Float, nullable=False)

    def to_dict(self):
        """Converte o objeto do banco de dados para um dicionário (JSON)"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class LoteCha(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_lote = db.Column(db.String(100), unique=True, nullable=False)
    data_preparo = db.Column(db.String(10), nullable=False)
    responsavel = db.Column(db.String(150), nullable=False)
    litros_iniciais = db.Column(db.Float, nullable=False)
    litros_atuais = db.Column(db.Float, nullable=False)
    observacoes = db.Column(db.String(300))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Utilizador, int(user_id))

# --- ROTAS DE NAVEGAÇÃO E AUTH ---

@app.route('/')
@login_required
def index():
    # Renderiza a interface única (SPA)
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Utilizador.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login inválido. Verifique o utilizador e a palavra-passe.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- API (ENDPOINTS JSON PARA O FRONT-END) ---

@app.route('/api/dados', methods=['GET'])
@login_required
def get_dados():
    """Retorna todos os dados de sessões e stock para preencher a interface."""
    sessoes = [s.to_dict() for s in Sessao.query.order_by(Sessao.id.desc()).all()]
    estoque = [l.to_dict() for l in LoteCha.query.order_by(LoteCha.id_lote).all()]
    return jsonify({'sessoes': sessoes, 'estoque': estoque})

@app.route('/api/sessoes', methods=['POST'])
@login_required
def add_sessao():
    """Adiciona uma nova sessão, atualiza o stock e gere retornos."""
    data = request.get_json()
    try:
        litros_finais = float(data['litros_finais'])
        
        # 1. Gestão de Retorno de Vegetal (Criar novo lote se solicitado)
        if data.get('registrar_retorno') and litros_finais > 0:
            id_lote_retorno = data['id_lote_retorno'].strip()
            # Verifica se o ID já existe para evitar erros
            if LoteCha.query.filter_by(id_lote=id_lote_retorno).first():
                return jsonify({'success': False, 'message': f'Já existe um lote com o ID "{id_lote_retorno}".'}), 400
            
            novo_lote_retorno = LoteCha(
                id_lote=id_lote_retorno,
                data_preparo=datetime.now().strftime('%d/%m/%Y'),
                responsavel="Sistema (Retorno)",
                litros_iniciais=litros_finais,
                litros_atuais=litros_finais,
                observacoes=f"Retorno da sessão: {data['sessao']}"
            )
            db.session.add(novo_lote_retorno)

        # 2. Dar baixa no Estoque (Deduzir dos lotes utilizados)
        for lote_str in data['lotes_utilizados'].split('|'):
            if not lote_str: continue
            id_lote, qtd = lote_str.split(':')
            lote_db = LoteCha.query.filter_by(id_lote=id_lote).first()
            if lote_db:
                lote_db.litros_atuais -= float(qtd)

        # 3. Registar a Sessão
        nova_sessao = Sessao(
            data_registro=datetime.now().strftime('%d/%m/%Y'),
            sessao=data['sessao'],
            data_sessao=datetime.strptime(data['data_sessao'], '%Y-%m-%d').strftime('%d/%m/%Y'),
            dirigente=data['dirigente'],
            explanacao=data.get('explanacao', ''),
            leitura_documentos=data.get('leitura_documentos', ''),
            responsavel_preenchimento=data['responsavel_preenchimento'],
            qtd_pessoas=int(data['qtd_pessoas']),
            lotes_utilizados=data['lotes_utilizados'],
            litros_iniciais=float(data['litros_iniciais']),
            litros_finais=litros_finais,
            litros_consumidos=float(data['litros_consumidos']),
            consumo_por_pessoa_ml=float(data['consumo_por_pessoa_ml'])
        )
        db.session.add(nova_sessao)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sessão registada com sucesso!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao registar: {str(e)}'}), 500

@app.route('/api/sessoes/<int:id>', methods=['DELETE'])
@login_required
def delete_sessao(id):
    sessao = db.session.get(Sessao, id)
    if sessao:
        db.session.delete(sessao)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sessão removida.'})
    return jsonify({'success': False, 'message': 'Sessão não encontrada.'}), 404

@app.route('/api/estoque', methods=['POST'])
@login_required
def add_lote():
    data = request.get_json()
    # Verifica duplicados
    if LoteCha.query.filter_by(id_lote=data['id_lote']).first():
        return jsonify({'success': False, 'message': 'ID de Lote já existe.'}), 400
    try:
        novo = LoteCha(
            id_lote=data['id_lote'],
            data_preparo=datetime.strptime(data['data_preparo'], '%Y-%m-%d').strftime('%d/%m/%Y'),
            responsavel=data['responsavel'],
            litros_iniciais=float(data['litros_iniciais']),
            litros_atuais=float(data['litros_iniciais']),
            observacoes=data.get('observacoes', '')
        )
        db.session.add(novo)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Lote adicionado.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/estoque/<int:id>', methods=['DELETE'])
@login_required
def delete_lote(id):
    lote = db.session.get(LoteCha, id)
    if lote:
        db.session.delete(lote)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Lote removido.'})
    return jsonify({'success': False, 'message': 'Lote não encontrado.'}), 404

# --- COMANDOS DE TERMINAL (CLI) ---

@app.cli.command("init-db")
def init_db():
    """Cria as tabelas na base de dados."""
    db.create_all()
    print("Base de dados criada/atualizada com sucesso.")

@app.cli.command("create-user")
def create_user():
    """Cria um novo utilizador via terminal."""
    u = input("Username: ")
    p = input("Password: ")
    with app.app_context():
        if Utilizador.query.filter_by(username=u).first():
            print("Erro: Utilizador já existe.")
            return
        nu = Utilizador(username=u)
        nu.set_password(p)
        db.session.add(nu)
        db.session.commit()
    print(f"Utilizador '{u}' criado com sucesso.")

if __name__ == '__main__':
    # Garante que as tabelas existem ao iniciar (útil para o Render)
    with app.app_context():
        db.create_all()
    app.run(debug=True)