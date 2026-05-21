from flask import Flask, redirect, render_template, request, url_for, flash
import api
from flask_caching import Cache
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user
import secrets
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)  # Generate a random secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DIR': 'cache'})

##########################################################
# Database
##########################################################

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

################################################
# Routes
################################################

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        
        else:
            flash('Invalid username or password. Please try again.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/')
def home():
    anime_data = get_anime_data()
    anime_names = anime_data['anime_list']
    anime_thumbnails = anime_data['anime_thumbnails']
    template_name = 'home_logged_in.html' if current_user.is_authenticated else 'home.html'
    return render_template(
        template_name,
        anime_list=anime_names,
        anime_thumbnails=anime_thumbnails,
        zip=zip,
        storage=None,
    )

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if username == '' or password == '':
            flash('Please fill out all fields.', 'error-message')
            return redirect(url_for('register'))
        else:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'error-message')
            else:
                new_user = User(username=username)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! You can now log in.', 'success-message')

    return render_template('register.html')

with app.app_context():
    db.create_all()

def get_anime_data():
    anime = api.get_anime_list(0)
    return {
        'anime_list': [a['data']['title'] for a in anime if a is not None],
        'anime_thumbnails': [a['data']['images']['jpg']['image_url'] for a in anime if a is not None],
        'zip': zip
    }