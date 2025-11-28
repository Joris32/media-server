from flask import Flask, send_from_directory, render_template, abort, request, jsonify, redirect, url_for, send_file, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
import re
import os
from functools import wraps
from pathlib import Path

# custom imports
from helper_functions import allowed_file, clean_filename, get_subtitle_url
from database import db, User, Media, MediaProgress, user_watched, create_media_object
from config import *

MEDIA_DIR = "../media"

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

admin_user = os.getenv("ADMIN_USERNAME")
admin_pass = os.getenv("ADMIN_PASSWORD")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///media-server.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username=admin_user).first():
        hashed_pw = generate_password_hash(admin_pass)
        admin = User(username=admin_user, password_hash=hashed_pw, is_admin=True)
        db.session.add(admin)
        db.session.commit()

def get_user():
    user_id = session.get("user_id", None)
    if user_id:
        user = User.query.filter_by(user_id=user_id).first()
        return user
    return None

def user_is_admin():
    user = get_user()
    if not user:
        return False
    return user.is_admin

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id", None)
        if not user_id:
            abort(401)
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not user_is_admin():
            abort(403)
        return f(*args, **kwargs)
    return wrapper
    
@app.route('/', defaults={'subpath': ''})
@app.route('/<path:subpath>')
def index(subpath):

    # search filters
    show_mp4_only = request.args.get('mp4_only') == 'true'
    show_unwatched = request.args.get('unwatched', 'false') == 'true'
    
    current_path = os.path.join(MEDIA_DIR, subpath)

    if not (os.path.exists(current_path) and os.path.isdir(current_path)):
        abort(404)

    # collect all filenames/folders in current subdirectory
    items = sorted(os.listdir(current_path), key = lambda x: x.upper())
    folders = [item for item in items if os.path.isdir(os.path.join(current_path, item)) and not item.startswith(".")]
    
    media_filenames = [item for item in items if item.endswith(tuple(VIDEO_EXT | BOOK_EXT))]
    
    subtitle_filenames = [item for item in items if item.endswith(tuple(SUBTITLE_EXT))]
    subtitle_basenames = [os.path.splitext(f)[0] for f in subtitle_filenames]

    # collect/create media objects for each media filename in current subdirectory
    media_list = [] 
    db_updated = False
    
    for filename in media_filenames:
        media_subpath = os.path.join(subpath, filename)
        media = Media.query.filter_by(subpath=media_subpath).first()

        # create media object if it doesn't exist
        if not media:
            media = create_media_object(filename, media_subpath, subtitle_basenames)

            db.session.add(media) # add new object to database
            db_updated = True

        else:
            # update whether existing media objects have subtitles
            has_subtitles = media.get_subtitles_bool(subtitle_basenames)

            if has_subtitles and not media.has_subtitles:
                # new subtitles were uploaded
                media.has_subtitles = True
                db_updated = True
                
            elif not has_subtitles and media.has_subtitles:
                # subtitles were removed
                media.has_subtitles = False
                db_updated = True
                
        media_list.append(media)
        
    if db_updated:
        db.session.commit()

    # applying search filters
    user = get_user()
    if user:
        watched_media = [media for media in user.watched_media]
    else:
        watched_media = []

    if show_mp4_only:
        media_list = [media for media in media_list if media.filename.endswith(".mp4")]
    if show_unwatched:
        media_list = [media for media in media_list if not media in watched_media]

    parent_path = str(Path(subpath).parent) if subpath else "" # path for "back" button
    
    return render_template("index.html", 
                           subpath=subpath, 
                           parent_path=parent_path, 
                           folders=folders, 
                           media_list=media_list, 
                           watched_media=watched_media, 
                           show_unwatched=show_unwatched, 
                           show_mp4_only=show_mp4_only, 
                           user=user,
                           info_popup_text=INFO_POPUP_TEXT)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    # POST
    username = request.form.get("username")
    password = request.form.get("password")

    if LOG_LOGIN_ATTEMPTS:
        ip = request.remote_addr

    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        if LOG_LOGIN_ATTEMPTS:
            print(f"login successful; username '{username}', ip '{ip}'")

        session["user_id"] = user.user_id
        return redirect(url_for("index"))

    if LOG_LOGIN_ATTEMPTS:
        print(f"login failed; username '{username}', ip '{ip}'")
        
    return render_template("login.html", error="Invalid credentials")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template("signup.html")

    # POST
    username = request.form.get('username').strip()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not username or not password or not confirm_password:
        return render_template("signup.html", error = "All fields required")

    existing_user = db.session.query(User).filter_by(username=username).first()
    if existing_user:
        return render_template("signup.html", error = "Username already taken")
        
    if password != confirm_password:
        return render_template("signup.html", error = "Passwords do not match")

    if LOG_LOGIN_ATTEMPTS:
        ip = request.remote_addr
        print(f"new user; username '{username}', ip '{ip}'")
        
    new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            is_admin=False)
    
    db.session.add(new_user)
    db.session.commit()
    session["user_id"] = new_user.user_id
    
    return redirect(url_for("index"))

    
@app.route('/play/<path:subpath>')
def play(subpath):
    
    media = Media.query.filter_by(subpath=subpath).first()
    full_path = os.path.join(MEDIA_DIR, subpath)
    
    if not media or not os.path.exists(full_path):
        abort(404)

    name = os.path.splitext(subpath)[0] # remove extension
    
    if media.is_book:
        book_url = url_for('media', subpath=subpath)
        return render_template("reader.html", book_name=name, book_url=book_url)
        
    video_url = f"/media/{subpath}" # endpoint that serves video files
    subtitle_url = get_subtitle_url(subpath, media_dir = MEDIA_DIR)
    
    user = get_user()
    logged_in = True if user else False
    
    return render_template("play.html", 
                           video_url=video_url, 
                           subtitle_url=subtitle_url, 
                           has_subtitles=media.has_subtitles, 
                           movie_name=name, 
                           media_id=media.media_id,
                           logged_in=logged_in)

@app.route('/toggle_watched', methods=['POST'])
# toggle "watched" status, so users can filter by unwatched content
@login_required
def toggle_watched():
    data = request.json or {}
    media_id = data.get("media_id")
    media = Media.query.get(media_id)
    
    if not media:
        abort(404)
        
    user = get_user()

    if media in user.watched_media:
        user.watched_media.remove(media)
        watched = False
    else:
        user.watched_media.append(media)
        watched = True
        
    db.session.commit()

    return jsonify({"message": f"Toggled {media.filename} watched status", "watched": watched}), 200


@app.route("/progress/<int:media_id>", methods=["GET", "POST"])
# used for both saving and retrieving a user's progress within a video
@login_required
def progress(media_id):
    user_id = session.get("user_id")
    
    if request.method == "GET":
        row = MediaProgress.query.filter_by(user_id=user_id, media_id=media_id).first()
        pos = row.position_seconds if row else 0
        
        if row:
            print(f"found pos: {pos}")
        else:
            print("no pos found")
            
        return jsonify({"position": pos})
    
    # POST    
    data = request.json or {}
    try:
        pos = float(data["position"])
    except:
        pos = 0.0

    print(f"saving pos: {pos}")
    
    row = MediaProgress.query.filter_by(user_id=user_id, media_id=media_id).first()
    if not row:
        row = MediaProgress(user_id=user_id, media_id=media_id)
        db.session.add(row)

    row.position_seconds = pos
    db.session.commit()

    return "", 204 # no content


@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    
    kwargs = {"allowed_extensions": ALLOWED_EXT}
    
    if request.method == 'GET':
        return render_template('upload.html', **kwargs)

    # POST
    if 'file' not in request.files:
        return render_template('upload.html', msg = "Error: no file part")
 
    file = request.files['file']

    if not file or file.filename == "":
        return render_template('upload.html', msg = "Error: no selected file")

    if not allowed_file(file.filename, allowed_extensions = ALLOWED_EXT):
        return render_template('upload.html', msg = "Error: invalid file type", **kwargs)
        
    filename = clean_filename(file.filename)
    filepath = os.path.join(MEDIA_DIR, filename)
    
    if os.path.exists(filepath):
        return render_template('upload.html', msg = f"Error: File '{filename}' already exists.", **kwargs)

    file.save(os.path.join(MEDIA_DIR, filename))
    return render_template('upload.html', msg =  f"File {filename} uploaded successfully.", **kwargs)
    
   
@app.route('/media/<path:subpath>') 
# not used when running with Docker (/media/ gets served by nginx)
def media(subpath):
    return send_from_directory(MEDIA_DIR, subpath)


if __name__ == '__main__':
    app.run(host=IP, port=DEV_PORT, debug=True)
