# Media Server

Python media server using Flask and Gunicorn. Made to stream videos and .epub books to other devices over Tailscale. 
Media directory can contain subfolders to organize media, which are easy to traverse through the interface.

## Usage

Run app.py to run in debug / development mode.

Run wsgi_launcher.py to run using Gunicorn (production mode).

## Features

- EPUB reading using JSZip and epub.js
- User registration and login
- Users can mark content as watched, and filter by unwatched content
- Admin accounts can use the page to upload files to media directory
- SQLAlchemy database is used for user accounts and progress tracking

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
```
