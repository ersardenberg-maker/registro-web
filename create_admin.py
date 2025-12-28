import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# --- CONFIGURAÇÃO MÍNIMA DA APP ---
app = Flask(__name__)
bcrypt = Bcrypt(app)

# --- O SEU URL DA RENDER (Já com aspas e corrigido) ---
DATABASE_URL = "postgresql://meu_banco_de_dados_ndes_user:cnPWQ7RzntxkPePLpjXfaDVttYngyLPF@dpg-d589ebbe5dus73dplk6g-a.oregon-postgres.render.com/meu_banco_de_dados_ndes"

# Garante compatibilidade do URL (caso venha como postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELO DE UTILIZADOR (Para saber onde criar) ---
class Utilizador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

# --- FUNÇÃO DE CRIAÇÃO ---
def criar_primeiro_utilizador():
    print("Conectando ao banco de dados na Render...")
    try:
        with app.app_context():
            # Cria as tabelas se não existirem
            db.create_all()

            # Verifica se já existe
            if Utilizador.query.first():
                print("AVISO: Já existem utilizadores registrados neste banco de dados.")
                continuar = input("Deseja criar outro? (s/n): ")
                if continuar.lower() != 's':
                    return

            username = input("Introduza o nome de utilizador: ")
            password = input("Introduza a palavra-passe: ")

            # Verifica duplicado específico
            if Utilizador.query.filter_by(username=username).first():
                print("Erro: Este utilizador já existe.")
                return

            new_user = Utilizador(username=username)
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            print("---------------------------------------------------")
            print(f"SUCESSO! Utilizador '{username}' criado no banco de dados da Render.")
            print("Agora pode fazer login no seu site online.")
            print("---------------------------------------------------")

    except Exception as e:
        print(f"ERRO DE CONEXÃO: {e}")
        print("Verifique se o seu IP está autorizado na Render ou se o URL está correto.")

if __name__ == '__main__':
    criar_primeiro_utilizador()

