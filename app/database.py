# database.py

from flask_sqlalchemy import SQLAlchemy
import os

from config import VIDEO_EXT, BOOK_EXT

db = SQLAlchemy() 

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

    def get_subtitles_bool(self, subtitle_basenames) -> bool:
        if not self.is_video:
            return False
        
        basename = os.path.splitext(self.filename)[0]
        return any(basename == stb for stb in subtitle_basenames) # matching subtitle file exists

class MediaProgress(db.Model):
    # for returning users to where they left off if they revisit a video
    __tablename__ = "media_progress"
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey("media.media_id"), primary_key=True)
    position_seconds = db.Column(db.Float, nullable=False, default=0)

    user = db.relationship("User")
    media = db.relationship("Media")
    
def create_media_object(filename, subpath, subtitle_basenames):
    is_video = filename.endswith(tuple(VIDEO_EXT))
    is_book = filename.endswith(tuple(BOOK_EXT))

    media = Media(filename=filename, 
                  is_video=is_video, 
                  is_book=is_book, 
                  subpath=subpath)

    media.has_subtitles = media.get_subtitles_bool(subtitle_basenames)
    return media