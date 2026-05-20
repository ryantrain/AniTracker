from flask import Flask, render_template, jsonify
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
    anime = api.get_anime_list(0)
    anime_names = [a['data']['title'] for a in anime if a is not None]
    anime_thumbnails = [a['data']['images']['jpg']['image_url'] for a in anime if a is not None]
    return render_template('home.html', anime_list=anime_names, anime_thumbnails=anime_thumbnails, zip=zip)

@app.route('/register/')
def register():
    return render_template('register.html')