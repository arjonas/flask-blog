from email.mime.text import MIMEText
from datetime import date
from functools import wraps
from flask import Flask, render_template, url_for, request, jsonify, flash
from flask import redirect as redireciona
import smtplib
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
# método que permite fazer relacionamento entre tabelas
from sqlalchemy.orm import relationship
# permite a criação de classes de maneira mais fácil.

# formularios
from flask_wtf import FlaskForm
from wtforms import StringField, validators
# Editor de texto
from flask_ckeditor import CKEditorField

# Flask sqlalchemy facilita o uso de sqlalchemy
from flask_sqlalchemy import SQLAlchemy
# Biblioteca para criptografia de senhas
from passlib.hash import pbkdf2_sha256

from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user

from flask_avatars import Avatars

NUMERO_MAXIMO_DE_POSTS = 5

today = date.today()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secreta'

# Configuracao Sqlite -Sqlalchemy usando flask_sqlalchemy
db = SQLAlchemy(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Blog.db'

login_manager = LoginManager()
login_manager.init_app(app)

avatars = Avatars(app)


# classe de usuarios
class Usuario(db.Model, UserMixin):

    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    senha = Column(String, nullable=False)
    ativo = Column(Boolean(), default=True)
    # relacionamentos
    posts_table = relationship('Post', back_populates='autor')
    comentarios = relationship('Comentario', back_populates='autor')
    respostas_comentarios = relationship('RespostaComentarios', back_populates='autor')

    # método para deletar usuario
    def deletar(self):
        db.session.delete(self)
        db.session.commit()


# Classe para criar tabela Post
class Post(db.Model):

    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    titulo = Column(String, nullable=False)
    subtitulo = Column(String, nullable=False)
    body = Column(String, nullable=False)
    data = Column(String, nullable=False)
    # relacionamentos
    comentario = relationship('Comentario', back_populates='post')
    autor = relationship('Usuario',  back_populates='posts_table')
    # chave estrangeira
    autor_id = Column(Integer, ForeignKey('users.id'))

    # método para deletar post
    def deletar(self):

        db.session.delete(self)
        db.session.commit()


class Comentario(db.Model):

    __tablename__ = 'comentarios'
    id = Column(Integer, primary_key=True)
    body = Column(String(100), nullable=False)
    # relacionamentos
    autor = relationship("Usuario", back_populates='comentarios')
    post = relationship('Post', back_populates='comentario')
    respostas = relationship('RespostaComentarios', back_populates='comentario')
    # chave estrangeiras
    autor_id = Column(Integer, ForeignKey('users.id'))
    post_id = Column(Integer, ForeignKey('posts.id'))

    # método para deletar comentario
    def deletar(self):

        db.session.delete(self)
        db.session.commit()


class RespostaComentarios(db.Model):

    __tablename__ = 'respostas'
    id = Column(Integer, primary_key=True)
    body = Column(String(100), nullable=False)
    coment_id = Column(Integer, ForeignKey('comentarios.id'))
    # relacionamentos
    comentario = relationship('Comentario', back_populates='respostas')
    autor = relationship('Usuario', back_populates='respostas_comentarios')
    # chave estrangeira
    autor_id = Column(Integer, ForeignKey('users.id'))


# metodo sqlaclhemy para criar  tabelas bancos de dados
db.create_all()

# Se não existe usuario administrador o cria e o adicona
if not Usuario.query.filter(Usuario.email == 'admin@admin.com').first():

        adm = Usuario(email='admin@admin.com', senha=pbkdf2_sha256.hash('1234567'),
                      username='administrador')

        db.session.add(adm)
        db.session.commit()


@login_manager.user_loader
def load_user(id_usuario):
    return Usuario.query.get(int(id_usuario))


# Classe formulario Wtform utilizado na pagina que adiona novos posts
class PostForm(FlaskForm):

    titulo = StringField('Titulo', validators=[validators.InputRequired()])
    subtitulo = StringField('Subtitulo', validators=[validators.InputRequired()])
    body = CKEditorField('Noticia')


# Classe formulario Wtform utilizado na pagina que adiona novos usuarios
class UserForm(FlaskForm):

    username = StringField('Nome', validators=[validators.InputRequired()])
    email = StringField('Email', validators=[validators.InputRequired()])
    password = StringField('Senha', validators=[validators.InputRequired()])


# Classe formulario Wtform utilizado na pagina login
class LoginForm(FlaskForm):

    email = StringField('Email', validators=[validators.InputRequired()])
    password = StringField('Senha', validators=[validators.InputRequired()])


# Classe formulario Wtform utilizado na pagina dos posts para comentar as noticias
class ComentForm(FlaskForm):

    comentario = CKEditorField('Comente')


# função para enviar emails utilizando smtplib
def enviar_email(nome, email, telefone, mensagem):

    SMTP_SERVER = "smtp.mail.yahoo.com"
    SMTP_PORT = 465
    SMTP_USERNAME = "sidnei.arjonas@yahoo.com"
    SMTP_PASSWORD = "hhpjcufhbybjhpnb"
    EMAIL_FROM = "sidnei.arjonas@yahoo.com"
    EMAIL_TO = "sidnei.arjonas@gmail.com"
    EMAIL_SUBJECT = "REMINDER:"
    co_msg = f"Olá sou o {nome} , aqui está meu email :{email} e o meu telefone:   {telefone}" \
             f"Gostaria de dizer:   {mensagem}"

    msg = MIMEText(co_msg)
    msg['Subject'] = "Novo contato"
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    debuglevel = True
    mail = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    mail.set_debuglevel(debuglevel)

    mail.login(SMTP_USERNAME, SMTP_PASSWORD)
    mail.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    mail.quit()


# decorador  que concede exclusividades a usuario adm de id 1 ao ser adicionado as rotas
def only_adm(f):

    @wraps(f)
    def funcao_decorada(*argumentos, **kargumentos):

        if current_user.get_id() != '1':

            return jsonify(error='Não autorizado'), 403

        else:

            return f(*argumentos, **kargumentos)

    return funcao_decorada


# Função que exclui posts antigos apartir da variavel NUMERO_MAXIMO_DE_POSTS
def exclui_antigos():

    resultado = Post.query.all()
    resultado.reverse()

    if len(resultado) > NUMERO_MAXIMO_DE_POSTS:

        # percorre os posts entre numero maximo de posts + 1
        for cont in range(NUMERO_MAXIMO_DE_POSTS, NUMERO_MAXIMO_DE_POSTS+1):
            # faz uma lista com os posts excluidos em ordem reversa da query
            # (para excluir os mais antigos)
            posts_excluidos = [resultado[cont] for post in resultado]

        for post in posts_excluidos:

            db.session.delete(post)
            db.session.commit()


# Rotas
# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Usuario.query.filter_by(email=email).first()

        # verica se existe o usuario com o email fonecido e se a senha fornecida bate
        if user and pbkdf2_sha256.verify(password, user.senha):

            login_user(user)

            return redireciona(url_for('home', username=user.username))
        else:

            if user:
                flash('Senha incorreta')
            else:
                flash('Email não cadastrado')

            return render_template('login.html', form=form)
    return render_template('login.html', form=form)


#  Logout
@app.route('/logout')
def logout():

    if current_user.is_authenticated:

        logout_user()

        return redireciona(url_for('home'))


#  Pagina inicial
@app.route('/')
def home():
    # função que exclui posts antigos
    exclui_antigos()
    # realiza query com os todos os posts
    posts = Post.query.all()
    # inverte a ordem da lista do resultado da query para os posts mais recentes ficarem encima
    posts.reverse()
    # pega os 3 primeiros posts
    posts = posts[:3]

    if current_user.is_authenticated:
        user = current_user.username
        return render_template("index.html", posts=posts, user=user)

    return render_template("index.html", posts=posts)


# Rota que retorna todos os posts na pagina inicial
@app.route('/all')
def todos_posts():

    posts = Post.query.all()
    posts.reverse()

    if current_user.is_authenticated:
        user = current_user.username
        return render_template("index.html", posts=posts, user=user)

    return render_template("index.html", posts=posts)


# Sobre
@app.route('/sobre')
def sobre():

    if current_user.is_authenticated:

        username = current_user.username

        return render_template('about.html', user=username)
    print('chegou')
    return render_template('about.html')


# Contato
@app.route('/contato',  methods=['POST', 'GET'])
def contato():

    if request.method == "POST":

        email = request.form['email']
        nome = request.form['name']
        telefone = request.form['phone']
        mensagem = request.form['message']

        enviar_email(nome, email, telefone, mensagem)

    if current_user.is_authenticated:

        username = current_user.username

        return render_template('contact.html', user=username)

    return render_template('contact.html')


# Adicionar novo post
@app.route('/novo', methods=['GET', 'POST'])
@only_adm
def novo_post():

    form = PostForm()
    if request.method == 'POST':

        new_post = Post(titulo=request.form['titulo'], subtitulo=request.form['subtitulo'],
                        body=request.form['body'],
                        data=f'{today.day}/{today.month}/{today.year}')

        #     adicionando ao banco
        db.session.add(new_post)
        db.session.commit()
        return redireciona(url_for('home'))

    return render_template('novo.html', form=form)


#  Retorna pagina com a noticia a partir de seu id
@app.route('/noticia/<id_post>')
def noticia(id_post):

    form = ComentForm()

    query_posts = Post.query.filter(Post.id == id_post)
    print(id)
    query_comentarios = Comentario.query.filter(Comentario.post_id == id_post)

    noticia_clicada = query_posts.first()
    comentarios_da_noticia = query_comentarios.all()
    print(comentarios_da_noticia)
    return render_template('post.html', noticia=noticia_clicada, form=form,
                           comentarios=comentarios_da_noticia)


# Rota para adicionar comentario ao banco de dados
@app.route('/coment', methods=['POST'])
def comentar():

    if request.method == 'POST':

        id_post_a_comentar = request.args.get('post_id')
        print(id)
        novo_comentario = Comentario(body=request.form['comentario'],
                                     autor_id=current_user.get_id(), post_id=id_post_a_comentar)

        db.session.add(novo_comentario)
        db.session.commit()

        return redireciona(url_for('noticia', id_post=id_post_a_comentar))


#  Rota para deletar um post do banco de dados
@app.route('/deletapost/<id_post_a_deletar>')
def deleta_post(id_post_a_deletar):

    noticia_a_deletar = Post.query.filter(Post.id == id_post_a_deletar).first()

    print(noticia_a_deletar.body)

    noticia_a_deletar.deletar()

    return redireciona(url_for('home'))


# Deleta comentarios feitos nos posts
@app.route('/delete/<id_coment>/<id_post>')
def deleta_comentario(id_coment, id_post):

    comentario_del = Comentario.query.filter(Comentario.id == id_coment).first()
    comentario_del.deletar()

    return redireciona(url_for('noticia', id_post=id_post))





# Rota para adiconar novo usuario ao banco de dados
@app.route('/registrar', methods=['GET', 'POST'])
def registrar():

    if request.method == 'POST':

        username = request.form['username']

        email = request.form['email']

        senha = request.form['password']

        # encriptografando senha
        senha_hash = pbkdf2_sha256.hash(senha)

        novo_usuario = Usuario(username=username, email=email, senha=senha_hash)

        db.session.add(novo_usuario)
        db.session.commit()

        return redireciona(url_for('login'))

    form = UserForm()

    if current_user.is_authenticated:

        username = current_user.username

        return render_template('registrar.html', user=username, form=form)

    return render_template('registrar.html', form=form)


# Rota para adm Banir usuarios
@app.route('/banir', methods=['GET', 'POST'])
def banimento():

    usuarios = Usuario.query.all()


    usernames = [user.username for user in usuarios]

    return render_template('usuarios.html', usuarios=usernames)





@app.route('/banir/<name>', methods=['GET', 'POST'])
def banir(name):

        usuarios = Usuario.query.all()
        usernames = [user.username for user in usuarios]

        if name != 'administrador'  :
            user_a_banir = Usuario.query.filter(Usuario.username==name).first()
            print(name)
            user_a_banir.deletar()

        return render_template('usuarios.html', usuarios=usernames)





if __name__ == '__main__':

    app.run(debug=True)
