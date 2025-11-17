import app
import os
from pathlib import Path

host = app.IP
port = app.PORT
access_logfile = app.ACCESS_LOGFILE
error_logfile = app.ERROR_LOGFILE

path = Path(access_logfile)
path.parent.mkdir(parents=True, exist_ok=True)
path.touch(exist_ok=True)

path = Path(error_logfile)
path.parent.mkdir(parents=True, exist_ok=True)
path.touch(exist_ok=True)

os.execvp("gunicorn", [
    "gunicorn",
    f"--bind={host}:{port}",
    f"--access-logfile={access_logfile}",
    f"--error-logfile={error_logfile}",
    f"--capture-output",
    "app:app"
])
