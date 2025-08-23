import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# --- CÓDIGO COPIADO DO SEU app.py ---
# É necessário para que o script entenda a estrutura da tabela de utilizadores.

app = Flask(__name__)
bcrypt = Bcrypt(app)

# --- O SEU URL DE CONEXÃO EXTERNA FOI INSERIDO AQUI ---
DATABASE_URL = "postgresql://banco_de_dados_sessoes_user:36ZuTYZIT345nVy8jJyrg9aIkVmEQbUi@dpg-d2ki313uibrs73e7f2pg-a.oregon-postgres.render.com/banco_de_dados_sessoes"

# --- CORREÇÃO APLICADA AQUI ---
# A verificação agora aceita "postgresql://"
if "postgres" not in DATABASE_URL:
    raise ValueError("Por favor, cole a sua 'External Connection String' da Render na variável DATABASE_URL.")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Utilizador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

# --- FUNÇÃO PRINCIPAL PARA CRIAR O UTILIZADOR ---
def criar_primeiro_utilizador():
    with app.app_context():
        # Cria as tabelas se ainda não existirem no banco de dados remoto
        db.create_all()

        # Verifica se já existe algum utilizador
        if Utilizador.query.count() > 0:
            print("Pelo menos um utilizador já existe. Nenhum novo utilizador foi criado.")
            return

        print("A criar o primeiro utilizador administrador...")
        username = input("Introduza o nome de utilizador desejado: ")
        password = input("Introduza a palavra-passe desejada: ")

        new_user = Utilizador(username=username)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"Utilizador '{username}' criado com sucesso no banco de dados da Render!")
        print("Pode agora fazer login na sua aplicação online.")

if __name__ == '__main__':
    criar_primeiro_utilizador()
