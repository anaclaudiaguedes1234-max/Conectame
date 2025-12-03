from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from flask_bcrypt import Bcrypt
from datetime import datetime

# --- CONFIG BÁSICA DO APP ---
app = Flask(__name__)

app.config['SECRET_KEY'] = 'segredo_super_secreto'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///conectame.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


# --- MODELOS ---

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    empresa = db.Column(db.String(100))
    status = db.Column(db.String(50))
    observacao = db.Column(db.String(300))
    lembrete = db.Column(db.String(20))  # estamos guardando como texto (YYYY-MM-DD)

    def __repr__(self):
        return f'<Cliente {self.nome}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)


# --- FLASK-LOGIN CONFIG ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- CRIA BANCO (E UM ADMIN SIMPLES) SE NÃO EXISTIR ---

with app.app_context():
    db.create_all()

    if not User.query.first():
        senha_hash = bcrypt.generate_password_hash("1234").decode('utf-8')
        admin = User(email="admin@admin.com", senha=senha_hash)
        db.session.add(admin)
        db.session.commit()
        print("Admin criado: admin@admin.com | senha: 1234")


# --- ROTAS ---

@app.route('/')
def home():
    return redirect('/login')


# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()

        usuario = User.query.filter_by(email=email).first()

        if usuario and bcrypt.check_password_hash(usuario.senha, senha):
            login_user(usuario)
            return redirect('/clientes')
        else:
            # depois podemos trocar isso por flash
            return "Usuário ou senha incorretos!"

    return render_template("login.html")


# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()

        if User.query.filter_by(email=email).first():
            return "Esse email já está em uso!"

        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_user = User(email=email, senha=senha_hash)
        db.session.add(novo_user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html')


# LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


# LISTAR CLIENTES + DASHBOARD SIMPLES
@app.route('/clientes')
@login_required
def listar_clientes():
    busca = request.args.get('busca', '').strip()

    query = Cliente.query
    if busca:
        like = f"%{busca}%"
        query = query.filter(
            (Cliente.nome.ilike(like)) |
            (Cliente.email.ilike(like)) |
            (Cliente.empresa.ilike(like))
        )

    clientes = query.all()

    # Contagens de status (no geral, não só filtrados)
    todos = Cliente.query.all()
    contagem = {
        'Novo': sum(1 for c in todos if c.status == 'Novo'),
        'Em andamento': sum(1 for c in todos if c.status == 'Em andamento'),
        'Fechado': sum(1 for c in todos if c.status == 'Fechado'),
        'Perdido': sum(1 for c in todos if c.status == 'Perdido'),
    }
    total_clientes = len(todos)

    return render_template(
        "clientes.html",
        clientes=clientes,
        busca=busca,
        datetime=datetime,
        contagem=contagem,
        total_clientes=total_clientes
    )


# FORM NOVO CLIENTE
@app.route('/novo')
@login_required
def novo_cliente():
    return render_template('adicionar.html')


# SALVAR NOVO CLIENTE
@app.route('/salvar', methods=['POST'])
@login_required
def salvar():
    novo = Cliente(
        nome=request.form.get('nome', ''),
        email=request.form.get('email', ''),
        telefone=request.form.get('telefone', ''),
        empresa=request.form.get('empresa', ''),
        status=request.form.get('status', ''),
        observacao=request.form.get('observacao', ''),
        lembrete=request.form.get('lembrete', '')
    )
    db.session.add(novo)
    db.session.commit()
    return redirect('/clientes')


# EDITAR CLIENTE
@app.route('/editar/<int:id>')
@login_required
def editar_id(id):
    cliente = Cliente.query.get_or_404(id)
    return render_template("editar.html", cliente=cliente)


# ATUALIZAR CLIENTE
@app.route('/atualizar/<int:id>', methods=['POST'])
@login_required
def atualizar(id):
    cliente = Cliente.query.get_or_404(id)

    cliente.nome = request.form.get('nome', '')
    cliente.email = request.form.get('email', '')
    cliente.telefone = request.form.get('telefone', '')
    cliente.empresa = request.form.get('empresa', '')
    cliente.status = request.form.get('status', '')
    cliente.observacao = request.form.get('observacao', '')
    cliente.lembrete = request.form.get('lembrete', '')

    db.session.commit()
    return redirect('/clientes')


# EXCLUIR CLIENTE
@app.route('/excluir/<int:id>')
@login_required
def excluir_id(id):
    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    return redirect('/clientes')


if __name__ == '__main__':
    app.run(debug=True)
