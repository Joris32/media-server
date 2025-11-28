# Media Server

Python media server using Docker, with a Flask + Gunicorn backend, media served using nginx. 
Made to stream videos and .epub books to other devices over Tailscale.
Media should be in `media/` folder in project directory. 
Media folder can contain subfolders to organize media, which are easy to traverse through the interface.

## Usage

### Using Docker

 1. Create `.env` file (see Environment Variables)
 2. Install Docker if not already installed
 3. Build and run Docker containers

  ```
  docker-compose up --build -d
  ```

 4. Navigate to `http://media` in a web browser from a device on your Tailnet (or `https://media.<tailnet-name>.ts.net` if using https)

### Without Docker

 1. Create `.env` file (see Environment Variables)
 2. Install dependencies
    
```
pip install -r requirements.txt
```

 3. Run `python app.py` to run in debug / development mode or run `python wsgi_launcher.py` to run using Gunicorn (production mode).
 4. Navigate to `http://localhost:8000` in a web browser (or, if using Tailscale, navigate to `http://<tailscale_ip>:8000` from a different device on your Tailnet)

## Features

- User registration and login
- Users can mark content as watched, and filter by unwatched content
- When logged in, server will keep track of progress within a video (users will be brought back to where they left off if they return to the video later)
- EPUB reading using JSZip and epub.js
- Admin accounts can use the page to upload files to media folder

## Environment Variables

Create a `.env` file in the project directory. 
Required keys:

```
SECRET_KEY=<flask-secret-key>

# admin account created on first run
ADMIN_USERNAME=<admin-username>
ADMIN_PASSWORD=<admin-password>
```

Required keys when using Docker:

```
TS_AUTHKEY=<ts-authkey>
```

Optional keys (only relevant when not using Docker):

```
# runs on localhost by default
TAILSCALE_IP=<tailscale-ip>

# sends logs to stderr/stdout by default
ACCESS_LOGFILE=logs/access.log
ERROR_LOGFILE=logs/stderr.log
```
