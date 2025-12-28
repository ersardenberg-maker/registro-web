import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)

# --- COLE AQUI A SUA URL EXTERNA DA RENDER ---
DATABASE_URL = "COLE_AQUI_O_URL_LONGO_QUE_TERMINA_EM_RENDER_COM"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Utilizador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

def criar():
    with app.app_context():
        db.create_all() # Garante que as tabelas existem
        u = input("User: ")
        p = input("Pass: ")
        if not Utilizador.query.filter_by(username=u).first():
            nu = Utilizador(username=u)
            nu.set_password(p)
            db.session.add(nu)
            db.session.commit()
            print("Criado!")
        else:
            print("Já existe.")

if __name__ == '__main__':
    criar()