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
@cache.cached(timeout=300)
def home():
    anime_data = get_anime_data()
    anime_names = anime_data['anime_list']
    anime_thumbnails = anime_data['anime_thumbnails']
    return render_template('home.html', anime_list=anime_names, anime_thumbnails=anime_thumbnails, zip=zip, \
                           storage=None)

@app.route('/register/')
def register():
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