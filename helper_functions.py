import re
import os
import json
import convert

def allowed_file(filename, allowed_extensions):
    return '.' in filename and os.path.splitext(filename)[1].lower() in allowed_extensions

def clean_filename(filename):
    filename = filename.strip()
    filename = filename.replace("\'", "`").replace("\"", "`") 
    filename = re.sub(r'[^\w\s.`-]', '', filename)
    return filename

def load_watched(watched_file):
    # legacy function
    if os.path.exists(watched_file):
        with open(watched_file, "r") as fp:
            return json.load(fp)
    return {}

def save_watched(watched_movies, watched_file):
    # legacy function
    with open(watched_file, "w") as fp:
        json.dump(watched_movies, fp, indent=4)

def get_subtitles(subpath, media_dir, verbose = False):
    # check if .vtt subtitles exist, if not check for .srt and convert to .vtt
    
    root = os.path.splitext(subpath)[0]
    subtitle_url = f"/media/{root}.vtt"
    subtitle_path = os.path.join(media_dir, f"{root}.vtt")

    if verbose:
        print("checking", subtitle_path)
    
    has_subtitles = os.path.exists(subtitle_path)  

    if has_subtitles and verbose:
        print("vtt subtitles found")
        return subtitle_url, True
        
    else:
        srt_path = os.path.join(media_dir, f"{root}.srt")

        if verbose:
            print("checking", srt_path)
    
        if os.path.exists(srt_path):
            if verbose:
                print("srt subtitles found")
            try:
                convert.to_utf_8(srt_path, verbose = verbose)
                convert.srt_to_vtt(srt_path, subtitle_path, verbose = verbose)
                return subtitle_url, True
            except Exception as e:
                if verbose:
                    print(".srt to .vtt conversion failed:", e)
                    print("subpath:", subpath)
                return "", False
            
        else:
            if verbose:
                print("no subtitles found")
            return "", False 