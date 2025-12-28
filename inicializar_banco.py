import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# --- CONFIGURAÇÃO ---
app = Flask(__name__)
bcrypt = Bcrypt(app)

# O seu URL de conexão externa com ?sslmode=require adicionado ao final
DATABASE_URL = "postgresql://banco_de_dados_sessoes_user:36ZuTYZIT345nVy8jJyrg9aIkVmEQbUi@dpg-d2ki313uibrs73e7f2pg-a.oregon-postgres.render.com/banco_de_dados_sessoes?sslmode=require"

# Correção de compatibilidade (caso o prefixo venha como postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DEFINIÇÃO COMPLETA DAS TABELAS ---

class Utilizador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

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
    lotes_utilizados = db.Column(db.String(500)) 
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

# --- EXECUÇÃO ---
def corrigir_banco():
    print("Conectando ao banco de dados na Render (Modo SSL)...")
    try:
        with app.app_context():
            print("Criando tabelas inexistentes (Sessao, LoteCha, Utilizador)...")
            db.create_all()
            print("✅ Sucesso! Todas as tabelas foram criadas.")
            
            if not Utilizador.query.first():
                print("⚠️ Nenhum utilizador encontrado. Vamos criar o administrador.")
                u = input("Username: ")
                p = input("Password: ")
                user = Utilizador(username=u)
                user.set_password(p)
                db.session.add(user)
                db.session.commit()
                print(f"Utilizador {u} criado.")
            else:
                print("ℹ️ Utilizadores já existem. Nenhuma ação necessária.")

    except Exception as e:
        print(f"❌ Erro de Conexão: {e}")
        print("\nDICA: Se o erro persistir, vá ao Dashboard da Render > PostgreSQL > Access Control")
        print("e adicione o IP '0.0.0.0/0' (Allow from anywhere) para garantir que o seu computador consegue entrar.")

if __name__ == '__main__':
    corrigir_banco()