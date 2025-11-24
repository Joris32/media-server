from flask import Flask, send_from_directory, render_template, abort, request, jsonify, redirect, url_for, send_file, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
import re
import os
from dotenv import load_dotenv
from functools import wraps

# custom imports
import convert
from helper_functions import allowed_file, clean_filename, get_subtitles


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

admin_user = os.getenv("ADMIN_USERNAME")
admin_pass = os.getenv("ADMIN_PASSWORD")
MEDIA_DIR = os.getenv("MEDIA_DIR", os.path.join(os.getcwd(), "media"))

IP = os.getenv("TAILSCALE_IP", "127.0.0.1")
WSGI_PORT = 8000 # port used when running wsgi_launcher.py
DEV_PORT = 8080 # port used when running app.py directly

ACCESS_LOGFILE = os.getenv("ACCESS_LOGFILE", "-")
ERROR_LOGFILE = os.getenv("ERROR_LOGFILE", "-") # print statements in app.py will end up here if gunicorn --capture-output is enabled

LOG_LOGIN_ATTEMPTS = True

VIDEO_EXT = {".mp4", ".mkv"}
BOOK_EXT = {".epub"}
SUBTITLE_EXT = {".srt", ".vtt"}
ALLOWED_EXTENSIONS = VIDEO_EXT | BOOK_EXT | SUBTITLE_EXT # for file uploading via /upload


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

user_watched = db.Table(
    'user_watched',
    db.Column('user_id', db.Integer, db.ForeignKey('user.user_id'), primary_key=True),
    db.Column('media_id', db.Integer, db.ForeignKey('media.media_id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    watched_media = db.relationship( # media marked as watched, for search filtering
        'Media',
        secondary=user_watched,
        back_populates='viewers'
    )

class Media(db.Model):
    __tablename__ = 'media'
    media_id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=False, nullable=False)
    subpath = db.Column(db.String(255), unique=True, nullable=False) # path to file, from MEDIA_DIR
    is_video = db.Column(db.Boolean, default=False, nullable=False)
    is_book = db.Column(db.Boolean, default=False, nullable=False)
    has_subtitles = db.Column(db.Boolean, default=False, nullable=False)
    
    viewers = db.relationship( # people who have marked piece of media as watched (for search filtering)
        'User',
        secondary=user_watched,
        back_populates='watched_media'
    )

class MediaProgress(db.Model):
    __tablename__ = "media_progress"
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey("media.media_id"), primary_key=True)
    position_seconds = db.Column(db.Float, nullable=False, default=0)

    user = db.relationship("User")
    media = db.relationship("Media")

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
    if user.is_admin:
        return True
    return False

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

    if not os.path.exists(current_path):
        return "Folder not found", 404

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

        # create object if it doesn't exist
        if not media:
            is_video = filename.endswith(tuple(VIDEO_EXT))
            is_book = filename.endswith(tuple(BOOK_EXT))
            
            if is_video:
                basename = os.path.splitext(filename)[0]
                has_subtitles = any(basename == stb for stb in subtitle_basenames) or filename.endswith(".mkv") # heuristic, most .mkv files have subtitles 
            else:
                has_subtitles = False

            media = Media(filename=filename, is_video=is_video, is_book=is_book, has_subtitles=has_subtitles, subpath=media_subpath)
            db.session.add(media) # add new object to database
            db_updated = True

        elif not filename.endswith(".mkv"):
            #check if subtitle files exist for existing media objects, in case they got removed or new ones uploaded
            basename = os.path.splitext(filename)[0]
            if any(basename == stb for stb in subtitle_basenames):
                if not media.has_subtitles:
                    media.has_subtitles = True
                    db_updated = True
            else:
                if media.has_subtitles:
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

    parent_path = "/".join(subpath.split("/")[:-1]) if subpath else "" # path for "back" button
    
    return render_template("index.html", subpath=subpath, parent_path=parent_path, folders=folders, media_list=media_list, watched_media=watched_media, show_unwatched=show_unwatched, show_mp4_only=show_mp4_only, user=user)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if LOG_LOGIN_ATTEMPTS:
            ip = request.remote_addr
            print(f"login attempt; username '{username}', ip '{ip}'")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.user_id
            if LOG_LOGIN_ATTEMPTS:
                print(f"login succesful; username '{username}', ip '{ip}'")
            return redirect(url_for("index"))
        else:
            if LOG_LOGIN_ATTEMPTS:
                print(f"login failed; username '{username}', ip '{ip}'")
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if LOG_LOGIN_ATTEMPTS:
            ip = request.remote_addr
            print(f"signup attempt; username '{username}', ip '{ip}'")

        if not username or not password or not confirm_password:
            return render_template("signup.html", error = "All fields required")

        existing_user = db.session.query(User).filter_by(username=username).first()
        if existing_user:
            return render_template("signup.html", error = "Username already taken")
            
        if password != confirm_password:
            return render_template("signup.html", error = "Passwords do not match")

        new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                is_admin=False
            )
        db.session.add(new_user)
        db.session.commit()
        session["user_id"] = new_user.user_id
        return redirect(url_for("index"))
            
    return render_template("signup.html")
    
@app.route('/play/<path:subpath>')
def play(subpath):
    full_path = os.path.join(MEDIA_DIR, subpath)
    if not os.path.exists(full_path):
        abort(404)

    ext = os.path.splitext(full_path)[1].lower()
    if ext == ".epub":
        
        book_name = os.path.splitext(subpath)[0]
        book_url = url_for('media', subpath=subpath)
        
        return render_template("reader.html", book_name=book_name, book_url=book_url)
        
    video_url = f"/media/{subpath}"
    subtitle_url, has_subtitles = get_subtitles(subpath, media_dir = MEDIA_DIR)
    movie_name = subpath.rsplit('.', 1)[0]

    media = Media.query.filter_by(subpath=subpath).first()
    if not media:
        abort(404)
    media_id = media.media_id

    user = get_user()
    logged_in = True if user else False
    return render_template("play.html", video_url=video_url, subtitle_url=subtitle_url, has_subtitles=has_subtitles, movie_name=movie_name, media_id=media_id, logged_in=logged_in)

@app.route('/toggle_watched', methods=['POST'])
@login_required
def toggle_watched():
    data = request.json
    media_id = data.get("media_id")
    media = Media.query.get(media_id)

    user = get_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if media in user.watched_media:
        user.watched_media.remove(media)
        watched = False
    else:
        user.watched_media.append(media)
        watched = True
    db.session.commit()

    return jsonify({"message": f"Toggled {media.filename} watched status", "watched": watched}), 200

@app.route("/progress/<int:media_id>", methods=["GET", "POST"])
@login_required
def progress(media_id):
    user_id = session.get("user_id")
    if request.method == "GET":
        row = MediaProgress.query.filter_by(user_id=user_id, media_id=media_id).first()
        pos = row.position_seconds if row else 0
        print("found pos", pos)
        return jsonify({"position": pos})
    
    #POST    
    data = request.get_json() or {}
    pos = float(data.get("position", 0))
    
    print("saving pos", pos)

    row = MediaProgress.query.filter_by(user_id=user_id, media_id=media_id).first()
    if not row:
        row = MediaProgress(user_id=user_id, media_id=media_id)
        db.session.add(row)

    row.position_seconds = pos
    db.session.commit()

    return "", 204

@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('upload.html', msg = "Error: no file part")
    
        file = request.files['file']
        
        if file.filename == '':
            return render_template('upload.html', msg = "Error: no selected file")
    
        if file and allowed_file(file.filename, allowed_extensions = ALLOWED_EXTENSIONS):
            filename = clean_filename(file.filename)
    
            filepath = os.path.join(MEDIA_DIR, filename)
            if os.path.exists(filepath):
                return render_template('upload.html', msg = f"Error: File '{filename}' already exists.", allowed_extensions = ALLOWED_EXTENSIONS)
    
            file.save(os.path.join(MEDIA_DIR, filename))
            return render_template('upload.html', msg =  f"File {filename} uploaded successfully.", allowed_extensions = ALLOWED_EXTENSIONS)
    
        return render_template('upload.html', msg = f"Error: invalid file type", allowed_extensions = ALLOWED_EXTENSIONS)
    return render_template('upload.html', allowed_extensions = ALLOWED_EXTENSIONS)

@app.route('/media/<path:subpath>')
def media(subpath):
    return send_from_directory(MEDIA_DIR, subpath)
    

if __name__ == '__main__':
    app.run(host=IP, port=DEV_PORT, debug=True)
