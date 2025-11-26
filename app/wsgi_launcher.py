# run this file to run using Gunicorn but without Docker

import app
import os
from pathlib import Path

host = app.IP
port = app.WSGI_PORT
access_logfile = app.ACCESS_LOGFILE
error_logfile = app.ERROR_LOGFILE

def ensure_file(path_str):
    if not path_str or path_str == "-":
        return
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)

ensure_file(access_logfile)
ensure_file(error_logfile)

os.execvp("gunicorn", [
    "gunicorn",
    f"--bind={host}:{port}",
    f"--access-logfile={access_logfile}",
    f"--error-logfile={error_logfile}",
    f"--capture-output",
    "--timeout=120",  
    "app:app"
])
