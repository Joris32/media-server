import re
import os
from chardet import detect

def is_srt(srt_file, verbose = False):
    if not os.path.isfile(srt_file):
        if verbose:
            print(f"'{srt_file}' does not exist")
        return False

    if not srt_file.lower().endswith('.srt'):
        if verbose:
            print(f"'{srt_file}' is not a .srt file")
        return False

    with open(srt_file, 'r', encoding='utf-8') as file:
        content = file.read()

    if not re.search(r"\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}", content):
        if verbose:
            print(f"'{srt_file}' does not have a valid srt format")
        return False

    return True


def srt_to_vtt(srt_file, vtt_file, verbose = True):
    if not is_srt(srt_file):
        return

    try:
        with open(srt_file, 'r', encoding='utf-8') as srt:
            lines = srt.readlines()

        with open(vtt_file, 'w', encoding='utf-8') as vtt:
            # add required WebVTT header
            vtt.write("WEBVTT\n\n")

            buffer = []
            for line in lines:
                line = line.strip()

                # skip srt block numbers
                if re.match(r"^\d+$", line):
                    continue

                # convert srt timestamps to vtt format
                if re.match(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}", line):
                    line = line.replace(",", ".")

                    if buffer:
                        vtt.write("\n".join(buffer) + "\n\n")
                        buffer = []

                buffer.append(line)

            if buffer:
                vtt.write("\n".join(buffer) + "\n\n")

        if verbose:
            print(f"conversion successful: {srt_file} -> {vtt_file}")

    except Exception as e:
        if verbose:
            print(f"error during conversion: {e}")

def get_encoding_type(file):
    with open(file, 'rb') as f:
        rawdata = f.read()
    return detect(rawdata)['encoding']

def to_utf_8(srcfile, verbose = True):

    from_codec = get_encoding_type(srcfile)
    
    if not from_codec:
        if verbose:
            print("unable to detect encoding")
        return
        
    if from_codec == "utf-8":
        if verbose:
            print("file is already utf-8 encoded")
        return

    root, ext = os.path.splitext(srcfile)
    trgfile = f"{root}_temp{ext}"

    try: 
        with open(srcfile, 'r', encoding=from_codec) as f, open(trgfile, 'w', encoding='utf-8') as e:
            while True:
                contents = f.read(4096)
                if not contents:
                    break
                e.write(contents)
    
        os.remove(srcfile) # remove old encoding file
        os.rename(trgfile, srcfile) # rename new encoding

        if verbose:
            print("file converted to utf-8")
    except UnicodeDecodeError:
        print("decode error")
    except UnicodeEncodeError:
        print("encode error")