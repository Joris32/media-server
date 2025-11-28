LOG_LOGIN_ATTEMPTS = True

VIDEO_EXT = {".mp4", ".mkv"}
BOOK_EXT = {".epub"}
SUBTITLE_EXT = {".srt", ".vtt"}
ALLOWED_EXT = VIDEO_EXT | BOOK_EXT | SUBTITLE_EXT # for file uploading via /upload

INFO_POPUP_TEXT = (
    "Log in to mark content as watched and filter by unwatched content. <br>"
    "Source code available "
    "<a href='https://github.com/Joris32/media-server' target='_blank'>"
    "on GitHub</a>."
)

# ------
# for running without Docker (running app.py or wsgi_launcher.py directly):
import os
from dotenv import load_dotenv
load_dotenv()

IP = os.getenv("TAILSCALE_IP", "127.0.0.1")

# used when running app.py directly
DEV_PORT = 8080

# used when running wsgi_launcher.py
WSGI_PORT = 8000
ACCESS_LOGFILE = os.getenv("ACCESS_LOGFILE", "-")
ERROR_LOGFILE = os.getenv("ERROR_LOGFILE", "-")