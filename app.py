import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

# --- CONFIGURAÇÃO DA APLICAÇÃO E EXTENSÕES ---
app = Flask(__name__)
app.secret_key = 'uma_chave_secreta_muito_segura_para_login'
bcrypt = Bcrypt(app)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'local_database.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- CONFIGURAÇÃO DO FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para aceder a esta página."
login_manager.login_message_category = "info"

# --- MODELOS DO BANCO DE DADOS ---
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
    data_registo = db.Column(db.String(10), nullable=False)
    id_sessao = db.Column(db.String(100), nullable=False)
    data_sessao = db.Column(db.String(10), nullable=False)
    dirigente = db.Column(db.String(150), nullable=False)
    explanacao = db.Column(db.String(200))
    leitura_documentos = db.Column(db.String(200))
    mestre_assistente = db.Column(db.String(150))
    responsavel_preenchimento = db.Column(db.String(150), nullable=False)
    qtd_pessoas = db.Column(db.Integer, nullable=False)
    lotes_utilizados = db.Column(db.String(300))
    litros_iniciais = db.Column(db.Float, nullable=False)
    litros_finais = db.Column(db.Float, nullable=False)
    litros_consumidos = db.Column(db.Float, nullable=False)
    consumo_por_pessoa_ml = db.Column(db.Float, nullable=False)

class LoteCha(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_lote = db.Column(db.String(100), unique=True, nullable=False)
    data_preparo = db.Column(db.String(10), nullable=False)
    responsavel = db.Column(db.String(150), nullable=False)
    litros_iniciais = db.Column(db.Float, nullable=False)
    litros_atuais = db.Column(db.Float, nullable=False)
    observacoes = db.Column(db.String(300))

@login_manager.user_loader
def load_user(user_id):
    return Utilizador.query.get(int(user_id))

# --- ROTAS DE AUTENTICAÇÃO ---
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
            flash('Login sem sucesso. Verifique o nome de utilizador e a palavra-passe.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão terminada com sucesso.', 'success')
    return redirect(url_for('login'))

# --- ROTAS DA APLICAÇÃO (PROTEGIDAS) ---
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/')
@login_required
def index():
    sessoes = Sessao.query.order_by(Sessao.id.desc()).all()
    return render_template('index.html', sessoes=sessoes)

@app.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar():
    lotes_cha = LoteCha.query.order_by(LoteCha.id_lote).all()
    if request.method == 'POST':
        try:
            form_data = request.form
            lotes_utilizados_str = form_data.get('lotes_utilizados_hidden')
            if not lotes_utilizados_str:
                flash('Erro: Nenhum lote de vegetal foi adicionado à sessão.', 'error')
                return render_template('adicionar.html', form_data=form_data, lotes_cha=lotes_cha)

            lotes_processados = []
            total_retirado_dos_lotes = 0
            for item in lotes_utilizados_str.split('|'):
                id_lote, qtd_str = item.split(':')
                qtd = float(qtd_str)
                lotes_processados.append({'id': id_lote, 'qtd': qtd})
                total_retirado_dos_lotes += qtd

            litros_finais_sessao = float(form_data.get('litros_finais'))
            litros_iniciais_sessao = total_retirado_dos_lotes
            litros_consumidos = round(litros_iniciais_sessao - litros_finais_sessao, 2)
            
            for lote_usado in lotes_processados:
                lote_inv = LoteCha.query.filter_by(id_lote=lote_usado['id']).first()
                if not lote_inv:
                    flash(f"Erro: O lote de vegetal com ID \"{lote_usado['id']}\" não foi encontrado no estoque.", 'error')
                    return render_template('adicionar.html', form_data=form_data, lotes_cha=lotes_cha)
                if lote_usado['qtd'] > lote_inv.litros_atuais:
                    flash(f"Erro: Quantidade retirada ({lote_usado['qtd']}L) do lote {lote_usado['id']} é maior que o estoque atual ({lote_inv.litros_atuais}L).", 'error')
                    return render_template('adicionar.html', form_data=form_data, lotes_cha=lotes_cha)
                lote_inv.litros_atuais = round(lote_inv.litros_atuais - lote_usado['qtd'], 2)

            qtd_pessoas = int(form_data.get('qtd_pessoas'))
            nova_sessao = Sessao(
                data_registo=datetime.now().strftime('%d/%m/%Y'),
                id_sessao=form_data.get('id_sessao'),
                data_sessao=datetime.strptime(form_data.get('data_sessao'), '%Y-%m-%d').strftime('%d/%m/%Y'),
                dirigente=form_data.get('dirigente'),
                explanacao=form_data.get('explanacao'),
                leitura_documentos=form_data.get('leitura_documentos'),
                mestre_assistente=form_data.get('mestre_assistente'),
                responsavel_preenchimento=form_data.get('responsavel_preenchimento'),
                qtd_pessoas=qtd_pessoas,
                lotes_utilizados=lotes_utilizados_str.replace('|', ' | '),
                litros_iniciais=litros_iniciais_sessao,
                litros_finais=litros_finais_sessao,
                litros_consumidos=litros_consumidos,
                consumo_por_pessoa_ml=round((litros_consumidos * 1000) / qtd_pessoas, 2) if qtd_pessoas > 0 else 0
            )
            db.session.add(nova_sessao)
            db.session.commit()
            flash('Sessão registada e estoque atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        except (ValueError, TypeError) as e:
            db.session.rollback()
            flash(f'Erro ao processar o formulário. Verifique os campos. Detalhe: {e}', 'error')
            return render_template('adicionar.html', form_data=request.form, lotes_cha=lotes_cha)
    
    return render_template('adicionar.html', form_data={}, lotes_cha=lotes_cha)

@app.route('/estoque')
@login_required
def estoque():
    lotes_cha = LoteCha.query.order_by(LoteCha.id_lote).all()
    total_vegetal = sum(lote.litros_atuais for lote in lotes_cha)
    return render_template('estoque.html', lotes_cha=lotes_cha, total_vegetal=total_vegetal)

@app.route('/adicionar_lote', methods=['POST'])
@login_required
def adicionar_lote():
    try:
        form_data = request.form
        novo_lote = LoteCha(
            id_lote=form_data.get('id_lote'),
            data_preparo=datetime.strptime(form_data.get('data_preparo'), '%Y-%m-%d').strftime('%d/%m/%Y'),
            responsavel=form_data.get('responsavel'),
            litros_iniciais=float(form_data.get('litros_iniciais')),
            litros_atuais=float(form_data.get('litros_iniciais')),
            observacoes=form_data.get('observacoes')
        )
        db.session.add(novo_lote)
        db.session.commit()
        flash('Novo lote adicionado ao estoque com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar lote. O ID do Lote já existe ou os dados são inválidos. Detalhe: {e}', 'error')
    return redirect(url_for('estoque'))

@app.route('/editar_lote/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_lote(id):
    lote_para_editar = LoteCha.query.get_or_404(id)
    if request.method == 'POST':
        try:
            form_data = request.form
            lote_para_editar.id_lote = form_data.get('id_lote')
            lote_para_editar.data_preparo = datetime.strptime(form_data.get('data_preparo'), '%Y-%m-%d').strftime('%d/%m/%Y')
            lote_para_editar.responsavel = form_data.get('responsavel')
            lote_para_editar.litros_iniciais = float(form_data.get('litros_iniciais'))
            lote_para_editar.litros_atuais = float(form_data.get('litros_atuais'))
            lote_para_editar.observacoes = form_data.get('observacoes')
            db.session.commit()
            flash('Lote atualizado com sucesso!', 'success')
            return redirect(url_for('estoque'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar. Verifique os campos. Detalhe: {e}', 'error')
            return render_template('editar_lote.html', lote=lote_para_editar)

    lote_para_editar.data_preparo_form = datetime.strptime(lote_para_editar.data_preparo, '%d/%m/%Y').strftime('%Y-%m-%d')
    return render_template('editar_lote.html', lote=lote_para_editar)

@app.route('/excluir_lote/<int:id>', methods=['POST'])
@login_required
def excluir_lote(id):
    lote_para_excluir = LoteCha.query.get_or_404(id)
    db.session.delete(lote_para_excluir)
    db.session.commit()
    flash('Lote excluído com sucesso!', 'success')
    return redirect(url_for('estoque'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    sessao_para_editar = Sessao.query.get_or_404(id)
    if request.method == 'POST':
        try:
            form_data = request.form
            sessao_para_editar.data_registo = form_data.get('data_registo')
            sessao_para_editar.id_sessao = form_data.get('id_sessao')
            sessao_para_editar.data_sessao = datetime.strptime(form_data.get('data_sessao'), '%Y-%m-%d').strftime('%d/%m/%Y')
            sessao_para_editar.dirigente = form_data.get('dirigente')
            sessao_para_editar.explanacao = form_data.get('explanacao')
            sessao_para_editar.leitura_documentos = form_data.get('leitura_documentos')
            sessao_para_editar.mestre_assistente = form_data.get('mestre_assistente')
            sessao_para_editar.responsavel_preenchimento = form_data.get('responsavel_preenchimento')
            sessao_para_editar.qtd_pessoas = int(form_data.get('qtd_pessoas'))
            sessao_para_editar.lotes_utilizados = form_data.get('lotes_utilizados')
            sessao_para_editar.litros_iniciais = float(form_data.get('litros_iniciais'))
            sessao_para_editar.litros_finais = float(form_data.get('litros_finais'))
            sessao_para_editar.litros_consumidos = round(sessao_para_editar.litros_iniciais - sessao_para_editar.litros_finais, 2)
            sessao_para_editar.consumo_por_pessoa_ml = round((sessao_para_editar.litros_consumidos * 1000) / sessao_para_editar.qtd_pessoas, 2) if sessao_para_editar.qtd_pessoas > 0 else 0
            
            db.session.commit()
            flash('Sessão atualizada com sucesso! (O estoque não foi alterado)', 'success')
            return redirect(url_for('index'))
        except (ValueError, TypeError):
            flash('Erro ao atualizar. Verifique os campos.', 'error')
            return render_template('editar.html', sessao=sessao_para_editar)

    sessao_para_editar.data_sessao_form = datetime.strptime(sessao_para_editar.data_sessao, '%d/%m/%Y').strftime('%Y-%m-%d')
    return render_template('editar.html', sessao=sessao_para_editar)

@app.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    sessao_para_excluir = Sessao.query.get_or_404(id)
    db.session.delete(sessao_para_excluir)
    db.session.commit()
    flash('Registo de sessão excluído com sucesso! (O estoque não foi alterado)', 'success')
    return redirect(url_for('index'))

@app.route('/consultas', methods=['GET', 'POST'])
@login_required
def consultas():
    if request.method == 'POST':
        query = Sessao.query
        dirigente_consulta = request.form.get('dirigente', '').strip()
        explanacao_consulta = request.form.get('explanacao', '').strip()
        leitura_consulta = request.form.get('leitura_documentos', '').strip()
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')

        if dirigente_consulta:
            query = query.filter(Sessao.dirigente.ilike(f'%{dirigente_consulta}%'))
        if explanacao_consulta:
            query = query.filter(Sessao.explanacao.ilike(f'%{explanacao_consulta}%'))
        if leitura_consulta:
            query = query.filter(Sessao.leitura_documentos.ilike(f'%{leitura_consulta}%'))
        
        sessoes = query.order_by(Sessao.id.desc()).all()
        resultado_filtrado = []

        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d') if data_inicio_str else None
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d') if data_fim_str else None

            for sessao in sessoes:
                data_sessao_obj = datetime.strptime(sessao.data_sessao, '%d/%m/%Y')
                if (not data_inicio or data_sessao_obj.date() >= data_inicio.date()) and \
                   (not data_fim or data_sessao_obj.date() <= data_fim.date()):
                    resultado_filtrado.append(sessao)

            return render_template('consultas.html', 
                                   resultado=resultado_filtrado, 
                                   total=len(resultado_filtrado),
                                   parametros=request.form)
        except ValueError:
            flash('Formato de data inválido. Use o seletor de datas.', 'error')
            return render_template('consultas.html', parametros=request.form)

    return render_template('consultas.html')

# --- COMANDOS DE LINHA DE COMANDOS (CLI) ---
@app.cli.command("init-db")
def init_db_command():
    """Cria as tabelas do banco de dados."""
    db.create_all()
    print("Banco de dados inicializado com sucesso.")

@app.cli.command("create-user")
def create_user():
    """Cria um novo utilizador."""
    username = input("Introduza o nome de utilizador: ")
    password = input("Introduza a palavra-passe: ")
    user = Utilizador.query.filter_by(username=username).first()
    if user:
        print(f"O utilizador {username} já existe.")
        return
    new_user = Utilizador(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    print(f"Utilizador {username} criado com sucesso!")

if __name__ == '__main__':
    app.run(debug=True)
