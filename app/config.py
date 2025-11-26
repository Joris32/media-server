LOG_LOGIN_ATTEMPTS = True

VIDEO_EXT = {".mp4", ".mkv"}
BOOK_EXT = {".epub"}
SUBTITLE_EXT = {".srt", ".vtt"}
ALLOWED_EXT = VIDEO_EXT | BOOK_EXT | SUBTITLE_EXT # for file uploading via /upload