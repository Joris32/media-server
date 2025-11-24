# Media Server

Python media server using Flask and Gunicorn. Made to stream videos and .epub books to other devices over Tailscale. 
Media directory can contain subfolders to organize media, which are easy to traverse through the interface.

## Usage

Run app.py to run in debug / development mode.

Run wsgi_launcher.py to run using Gunicorn (production mode).

## Features

- User registration and login
- Users can mark content as watched, and filter by unwatched content
- When logged in, server will keep track of progress within a video (users will be brought back to where they left off if they return to the video later)
- EPUB reading using JSZip and epub.js
- Admin accounts can use the page to upload files to media directory

## Environment Variables

Create a `.env` file in the project directory. Required keys:

```
SECRET_KEY=<flask-secret-key>

# admin account created on first run
ADMIN_USERNAME=<admin-username>
ADMIN_PASSWORD=<admin-password>
```

Optional keys:

```
MEDIA_DIR=media

# runs on localhost by default, change to your local Tailscale IP to access over Tailscale
TAILSCALE_IP=127.0.0.1

# by default server will send logs to stderr/stdout
ACCESS_LOGFILE=logs/access.log
ERROR_LOGFILE=logs/stderr.log
```
