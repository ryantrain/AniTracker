from flask import Flask, redirect, render_template, request, url_for, flash
import api
from flask_caching import Cache
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
import secrets
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableList
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__, instance_path='/tmp/instance')
app.config['SECRET_KEY'] = secrets.token_hex(32)  # Generate a random secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') 
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DIR': 'cache'})

ALLOWED_BOOKMARK_STATUSES = ('Watching', 'Completed', 'Dropped', 'Waiting to Air')

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
    bio = db.Column(db.String(500), nullable=True, default='')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, salt_length=32)
        db.session.commit()
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_email(self, email):
        self.email = email if email else None

    def check_email(self, email):
        return self.email == email

    def _normalize_bookmark_status(self, status):
        return status if status in ALLOWED_BOOKMARK_STATUSES else 'Watching'

    def _normalize_bookmark_entry(self, bookmark):
        if isinstance(bookmark, dict):
            anime_id = bookmark.get('anime_id', bookmark.get('mal_id', bookmark.get('id')))
            status = self._normalize_bookmark_status(bookmark.get('status', 'Watching'))
        else:
            anime_id = bookmark
            status = 'Watching'

        if anime_id is None:
            return None

        return {
            'anime_id': int(anime_id),
            'status': status,
        }

    def normalize_bookmarks(self):
        normalized_bookmarks = []
        changed = False

        for bookmark in self.bookmarks or []:
            normalized_bookmark = self._normalize_bookmark_entry(bookmark)
            if normalized_bookmark is None:
                continue

            normalized_bookmarks.append(normalized_bookmark)
            if normalized_bookmark != bookmark:
                changed = True

        if changed:
            self.bookmarks = normalized_bookmarks
            db.session.commit()

        return normalized_bookmarks

    def get_bookmark_entry(self, anime_id):
        anime_id = int(anime_id)
        for bookmark in self.normalize_bookmarks():
            if bookmark['anime_id'] == anime_id:
                return bookmark
        return None

    def get_bookmark_status(self, anime_id):
        bookmark = self.get_bookmark_entry(anime_id)
        return bookmark['status'] if bookmark else None
    
    def add_bookmark(self, anime_id):
        self.add_bookmark_with_status(anime_id, 'Watching')

    def add_bookmark_with_status(self, anime_id, status):
        anime_id = int(anime_id)
        status = self._normalize_bookmark_status(status)
        bookmarks = self.normalize_bookmarks()
        updated = False

        for bookmark in bookmarks:
            if bookmark['anime_id'] == anime_id:
                bookmark['status'] = status
                updated = True
                break

        if not updated:
            bookmarks.append({'anime_id': anime_id, 'status': status})

        self.bookmarks = bookmarks
        db.session.commit()
    
    def remove_bookmark(self, anime_id):
        anime_id = int(anime_id)
        bookmarks = self.normalize_bookmarks()
        filtered_bookmarks = [bookmark for bookmark in bookmarks if bookmark['anime_id'] != anime_id]

        if len(filtered_bookmarks) != len(bookmarks):
            self.bookmarks = filtered_bookmarks
            db.session.commit()

    def set_bookmark_status(self, anime_id, status):
        anime_id = int(anime_id)
        status = self._normalize_bookmark_status(status)
        bookmarks = self.normalize_bookmarks()
        found = False

        for bookmark in bookmarks:
            if bookmark['anime_id'] == anime_id:
                bookmark['status'] = status
                found = True
                break

        if not found:
            bookmarks.append({'anime_id': anime_id, 'status': status})

        self.bookmarks = bookmarks
        db.session.commit()
    
    def set_profile_picture(self, filename):
        if self.profile_picture != 'default-icon.png': 
                path = os.path.join(app.root_path, 'static', 'images', self.profile_picture)
                os.remove(path)
        self.profile_picture = filename
        db.session.commit()

    def set_username(self, username):
        self.username = username
        db.session.commit()

    def set_bio(self, bio: str):
        self.bio = bio
        db.session.commit()


class FeaturedAnime(db.Model):
    mal_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(512), nullable=False)
    ranking = db.Column(db.Integer, nullable=True)


def seed_featured_anime():
    """
    Seeds the FeaturedAnime table with the top 20 anime from the API.
    This function must be run every time the database is wiped to reload and database for
    anime data to be displayed.
    """
    featured_count = FeaturedAnime.query.count()
    if featured_count >= 20:
        return

    existing_ids = {anime.mal_id for anime in FeaturedAnime.query.all()}

    for anime in api.get_top_anime().get('data', [])[:20]:
        if anime['mal_id'] in existing_ids:
            continue

        anime_data = api.search_anime_by_id(anime['mal_id'])
        if not anime_data or 'data' not in anime_data:
            continue

        data = anime_data['data']
        image_url = data['images']['jpg']['large_image_url']

        db.session.add(
            FeaturedAnime(
                mal_id=data['mal_id'],
                title=data['title'],
                image_url=image_url,
                ranking=anime.get('rank')
            )
        )

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
            return redirect(url_for('login', next=next_page))

    return render_template('login.html', next_page=next_page)

@app.route('/', methods=['GET', 'POST'])
def home():

    if current_user.is_authenticated and request.method == 'POST':
        if request.form.get('logout'):
            logout_user()
            return redirect(url_for('home'))

    anime_data = FeaturedAnime.query.order_by(FeaturedAnime.ranking.asc(), FeaturedAnime.mal_id.asc()).limit(20).all()
    if len(anime_data) != 20:
        seed_featured_anime()
        anime_data = FeaturedAnime.query.order_by(FeaturedAnime.ranking.asc(), FeaturedAnime.mal_id.asc()).limit(20).all()

    return render_template(
        'home.html',
        anime_list=anime_data,
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

@app.route('/profile/<string:username>/', methods=['GET', 'POST'])
def profile(username):
    if request.method == 'POST':
        if current_user.is_authenticated:
            if request.form.get('logout'):
                logout_user()
                return redirect(url_for('profile', username=username))
            
            if request.form.get('new_username'):
                new_username = request.form.get('new_username')
                if new_username and new_username != current_user.username:
                    if User.query.filter_by(username=new_username).first():
                        flash('Username already taken. Please choose a different one.', 'name-error-message')
                    else:
                        current_user.set_username(new_username)
                        flash('Username updated successfully.', 'name-success-message')
                        return redirect(url_for('profile', username=new_username))
                else:
                    flash('Please enter a valid username.', 'name-error-message')

            if request.form.get('current_password'):
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_new_password = request.form.get('confirm_new_password')

                if not current_user.check_password(current_password):
                    flash('Current password is incorrect. Please try again.', 'password_wrong-error-message')

                elif new_password == '':
                    flash('New password cannot be empty. Please try again.', 'password_empty-error-message')
                
                elif new_password != confirm_new_password:
                    flash('New passwords do not match. Please try again.', 'password_mismatch-error-message')
                
                else:
                    current_user.set_password(new_password)
                    flash('Password updated successfully.', 'password-success-message')
                    return redirect(url_for('profile', username=username))
            
            if (request.form.get('new_password') or request.form.get('confirm_new_password')) and not request.form.get('current_password'):
                flash('Please enter your current password to change your password.', 'password_current-error-message')
            if request.form.get('new_bio'):
                new_bio = request.form.get('new_bio')
                current_user.set_bio(new_bio)
                flash('Bio updated successfully.', 'bio-success-message')
                return redirect(url_for('profile', username=username))

    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', user=user)

@app.route('/search/', methods=['GET', 'POST'])
@app.route('/search/<path:query>/', methods=['GET', 'POST'])
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

@app.route('/anime/<path:title>/<int:id>/', methods= ['GET', 'POST'])
def anime(title, id):

    search_results = api.search_anime_by_id(id)
    anime_info = search_results['data'] if search_results and 'data' in search_results else None

    if request.method == 'POST':
        if current_user.is_authenticated:
            if request.form.get('logout'):
                logout_user()
                return redirect(url_for('anime', title=title, id=id))
            
            if request.form.get('bookmark_action') == 'remove':
                current_user.remove_bookmark(id)
                return redirect(url_for('anime', title=title, id=id))

            if request.form.get('bookmark_status'):
                current_user.set_bookmark_status(id, request.form.get('bookmark_status'))
                return redirect(url_for('anime', title=title, id=id))

            if request.form.get('bookmark_action') == 'add':
                default_bookmark_status = 'Waiting to Air' if anime_info and anime_info.get('status') == 'Not yet aired' else 'Watching'
                current_user.add_bookmark_with_status(id, default_bookmark_status)
                return redirect(url_for('anime', title=title, id=id))

    current_bookmark = current_user.get_bookmark_entry(id) if current_user.is_authenticated else None
    is_bookmarked = current_bookmark is not None
    authenticated = current_user.is_authenticated
    current_bookmark_status = current_bookmark['status'] if current_bookmark else None

    return render_template(
        'anime.html',
        anime_info=anime_info,
        authenticated=authenticated,
        is_bookmarked=is_bookmarked,
        current_bookmark_status=current_bookmark_status,
        requested_title=title,
        requested_id=id,
    )

@app.route('/bookmarks/')
@login_required
def bookmarks():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    current_user.normalize_bookmarks()
    anime_list = []
    for bookmark in current_user.bookmarks:
        anime_data = api.search_anime_by_id(bookmark['anime_id'])
        if anime_data and 'data' in anime_data:
            bookmarked_anime = anime_data['data'].copy()
            bookmarked_anime['bookmark_status'] = bookmark['status']
            anime_list.append(bookmarked_anime)
    return render_template('bookmarks.html', anime_list=anime_list)

@app.route('/upload',  methods=['POST'])
@login_required
def upload():
    if request.method == 'POST':

        if 'profile_picture_upload' not in request.files:
            return redirect(url_for('profile', username=current_user.username))
        
        file = request.files['profile_picture_upload']

        if file.filename == '':
            return redirect(url_for('profile', username=current_user.username))
        
        if file:
            filename = f"{current_user.id}_{secure_filename(file.filename)}"
            file.save(f'static/images/{filename}')
            current_user.set_profile_picture(filename)
            return redirect(url_for('profile', username=current_user.username))
        
@app.route('/update_bio', methods=['POST'])
@login_required
def update_bio():
    if request.method == 'POST':
        new_bio = request.form.get('bio', '')
        current_user.bio = new_bio
        db.session.commit()
        return redirect(url_for('profile', username=current_user.username))

with app.app_context():
    db.create_all()