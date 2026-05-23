from flask import Flask, redirect, render_template, request, url_for, flash
import api
from flask_caching import Cache
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
import secrets
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableList
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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
    email = db.Column(db.String(150), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.now().date())
    profile_picture = db.Column(db.String(256), nullable=True, default='default-icon.png')
    bookmarks = db.Column(MutableList.as_mutable(db.JSON), nullable=False, default=list)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, salt_length=32)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_email(self, email):
        self.email = email if email else None

    def check_email(self, email):
        return self.email == email
    
    def add_bookmark(self, anime_id):
        if anime_id not in self.bookmarks:
            self.bookmarks.append(anime_id)
            db.session.commit()
    
    def remove_bookmark(self, anime_id):
        if anime_id in self.bookmarks:
            self.bookmarks.remove(anime_id)
            db.session.commit()


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

    next_page = request.args.get('next')
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.form.get('next')
            return redirect(next_page)
        
        else:
            flash('Invalid username or password. Please try again.')
            return redirect(url_for('login'))

    return render_template('login.html', next_page=next_page)

@app.route('/', methods=['GET', 'POST'])
def home():

    if current_user.is_authenticated and request.method == 'POST':
        if request.form.get('logout'):
            logout_user()
            return redirect(url_for('home'))
        
    anime_data = get_anime_data()
    anime_names = anime_data['anime_list']
    anime_thumbnails = anime_data['anime_thumbnails']
    template_name = 'home_logged_in.html' if current_user.is_authenticated else 'home.html'
    current_username = current_user.username if current_user.is_authenticated else None
    return render_template(
        template_name,
        anime_list=anime_names,
        anime_thumbnails=anime_thumbnails,
        zip=zip,
        current_username=current_username,
        storage=None,
    )

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if username == '' or password == '' or confirm_password == '':
            flash('Please fill out all fields.', 'error-message')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error-message')
            return redirect(url_for('register'))
        
        else:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'error-message')
                return redirect(url_for('register'))
            
            else:
                new_user = User(username=username)
                new_user.set_password(password)
                new_user.set_email(request.form.get('email', None))
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! You can now log in.', 'success-message')

    return render_template('register.html')

@app.route('/profile/<string:username>/')
@login_required
def profile(username):
    current_username = current_user.username if current_user.is_authenticated else None
    profile_picture = current_user.profile_picture if current_user.is_authenticated else None
    return render_template('profile.html', current_username=current_username, profile_picture=profile_picture)

@app.route('/search/', methods=['GET', 'POST'])
@app.route('/search/<string:query>/', methods=['GET', 'POST'])
def search(query=None):

    if request.method == 'POST':
        if current_user.is_authenticated:
            if request.form.get('logout'):
                logout_user()
                query = query or request.args.get('Search_Bar', '')
                page = request.args.get('page', default=1, type=int)
                return redirect(url_for('search', query=query, page=page))

    authenticated = current_user.is_authenticated
    query = query or request.args.get('Search_Bar', '')
    page = request.args.get('page', default=1, type=int)
    if page < 1:
        page = 1
    search_results = api.search_anime_by_title(query, page) if query else []
    anime_info = search_results['data'] if 'data' in search_results else []
    pagination_info = search_results['pagination'] if 'pagination' in search_results else {}
    current_username = current_user.username if current_user.is_authenticated else None
    anime_titles = [anime['title'].replace(' ', '-') for anime in anime_info]

    return render_template('search.html', 
            anime_info=anime_info,
            pagination_info=pagination_info,
            anime_titles=anime_titles,
            query=query,
            authenticated=authenticated,
            current_username=current_username,
            zip=zip,
        )

@app.route('/anime/<string:title>/<int:id>/', methods= ['GET', 'POST'])
def anime(title, id):

    if request.method == 'POST':
        if current_user.is_authenticated:
            if request.form.get('logout'):
                logout_user()
                return redirect(url_for('anime', title=title, id=id))
            
            if request.form.get('bookmark_action'):

                if request.form.get('bookmark_action') == 'remove':
                    current_user.remove_bookmark(id)
                    return redirect(url_for('anime', title=title, id=id))
                
                elif request.form.get('bookmark_action') == 'add':
                    current_user.add_bookmark(id)
                    return redirect(url_for('anime', title=title, id=id))

    is_bookmarked = id in current_user.bookmarks if current_user.is_authenticated else False
    authenticated = current_user.is_authenticated
    search_results = api.search_anime_by_id(id)
    anime_info = search_results['data'] if 'data' in search_results else []
    return render_template('anime.html', anime_info=anime_info, authenticated=authenticated
                           , is_bookmarked=is_bookmarked)

with app.app_context():
    db.create_all()

def get_anime_data():
    anime = api.get_anime_list(0)
    return {
        'anime_list': [a['data']['title'] for a in anime if a is not None],
        'anime_thumbnails': [a['data']['images']['jpg']['image_url'] for a in anime if a is not None],
        'zip': zip
    }
