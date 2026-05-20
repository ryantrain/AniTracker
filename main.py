from flask import Flask, render_template, request
import api
from flask_caching import Cache

app = Flask(__name__)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DIR': 'cache'})

@app.route('/login/')
def login():
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

def get_anime_data():
    anime = api.get_anime_list(0)
    return {
        'anime_list': [a['data']['title'] for a in anime if a is not None],
        'anime_thumbnails': [a['data']['images']['jpg']['image_url'] for a in anime if a is not None],
        'zip': zip
    }