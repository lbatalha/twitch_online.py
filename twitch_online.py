#!/bin/env python3

import os, sys, argparse

import requests, yaml, gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify, GdkPixbuf

state_base_path = os.path.join(os.environ['XDG_STATE_HOME'], 'twitch_online')
default_output_file = os.path.join(state_base_path, 'status')
default_title_file= os.path.join(state_base_path, 'title')
default_token_file = os.path.join(state_base_path, 'token')
default_cred_file = os.path.join(os.environ['XDG_CONFIG_HOME'], 'twitch_online.creds')
game_image_size = "150x150"

parser = argparse.ArgumentParser(description="CLI Utility to check if a twitch channel is streaming", \
        epilog="The credentials file should be a simple yaml file with `client_id` and `client_secret` variables")
parser.add_argument('-c', '--cred-file', default=default_cred_file, help="File used to store credentials")
parser.add_argument('-a', '--token-file', default=default_token_file, help="File used to store temporary auth token")
parser.add_argument('-o', '--output-file', default=default_output_file, help="File used to store custom liveness output")
parser.add_argument('-t', '--title-file', default=default_title_file, help="File used to store title for title change checks")
parser.add_argument('-l', '--live-text', default="🔴", help="Text writen to output-file when CHANNEL is live")
parser.add_argument('-i', '--get-image', default=True, help="Whether to get the game box art image")
parser.add_argument('CHANNEL', help="Channel to check")

args = vars(parser.parse_args())
cred_file = args['cred_file']
token_file = args['token_file']
output_file = args['output_file']
title_file = args['title_file']
live_text = args['live_text']
get_game_image = args['get_image']

sensitive_files = [token_file, cred_file]

# Ensure state directory exists
if not os.path.isdir(state_base_path):
    sys.stderr.write(f"State directory not found, creating at {state_base_path}\n")
    os.mkdir(state_base_path, 0o700)

# Init persistent files
for file in [token_file, title_file, cred_file]:
    if not os.path.isfile(file):
        sys.stderr.write(f"Creating missing file at {file}\n")
        with open(file, 'w') as f:
            f.write('')
        # Ensure only calling user can read contents
        if file in sensitive_files and os.stat(file).st_mode != 0o600:
            sys.stderr.write(f"Securing sensitive file {file}\n")
            os.chmod(file, 0o600)

# Handle reading config yaml
with open(cred_file, 'r') as f:
    try:
        config = yaml.safe_load(f)
        client_id = config['client_id']
        client_secret = config['client_secret']
    except yaml.YAMLError as pe:
        sys.stderr.write(f"Failed to parse credentials file at {cred_file}\n")
        sys.stderr.write(pe+"\n")
        sys.exit(128)


def check_status():
    with open(token_file, 'r') as f:
        auth_token = f.read(256).rstrip('\n')
    auth_headers = {'Authorization': 'Bearer ' + auth_token, \
            'Client-Id': client_id}
    users = requests.get('https://api.twitch.tv/helix/users', timeout=1, \
            params={'login': args['CHANNEL']}, \
            headers=auth_headers)
    if users.status_code == 401:
        sys.stderr.write("401: Authentication failed, re-authenticating\n")
        authenticate()
        sys.exit(2)
    elif users.status_code != 200:
        sys.stderr.write(f"Unhandled API status code: {users.status_code}\n")
        sys.stderr.write(users.text+"\n")
        sys.exit(3)

    streams = requests.get('https://api.twitch.tv/helix/streams', timeout=1, \
            params={'user_login': args['CHANNEL']}, \
            headers=auth_headers)
    channels = requests.get('https://api.twitch.tv/helix/channels', timeout=1, \
        params={'broadcaster_id': users.json()['data'][0]['id']}, \
        headers=auth_headers)

    image = None
    if get_game_image:
        games = requests.get('https://api.twitch.tv/helix/games', timeout=1, \
            params={'id': channels.json()['data'][0]['game_id']}, \
            headers=auth_headers)

        image_url = games.json()['data'][0]['box_art_url'].replace("{width}x{height}", game_image_size)
        image_req = requests.get(image_url, timeout=1, stream=True)

        if image_req.status_code != 200:
            sys.stderr.write(f"Failed to get game box art at {image_url}\n")
        else:
            loader = GdkPixbuf.PixbufLoader()
            # Produces same output as .write_bytes(GLib.Bytes.new(image_req.content))
            loader.write(image_req.content)
            loader.close()
            image = loader.get_pixbuf()

    return [users, streams, channels, image]

def authenticate():
    try:
        auth = requests.post('https://id.twitch.tv/oauth2/token', timeout=5, params={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials',
        })
        auth.raise_for_status()
    except requests.HTTPError as e:
        note = Notify.Notification.new(f"Exception:", e)
        note.set_timeout(Notify.EXPIRES_NEVER)
        note.set_urgency(2)
        note.show()

    auth_data = auth.json()
    with open(token_file, 'w') as f:
        f.write(auth_data['access_token'])

# Used to check and notify for title changes
def title_check(channel, image):
    title = channel['title']
    with open(title_file, 'r+') as f:
        current_title = f.read()
        if current_title != title:
            note = Notify.Notification.new(f"{channel['broadcaster_name']} twitch:", f"{title}")
            note.set_timeout(Notify.EXPIRES_NEVER)
            note.set_urgency(1)
            if image:
                note.set_image_from_pixbuf(image)
            note.show()
            f.seek(0)
            f.write(title)
            f.truncate()

# Used to check and set liveness status
def liveness_check(status):
    with open(output_file, 'w') as f:
        if status.json()['data'] and status.json()['data'][0]['type'] == 'live':
            f.write(live_text)
        else:
            f.write("")

def main():
    response = check_status()
    liveness_check(response[1])
    Notify.init("twitch_online.py")
    title_check(response[2].json()['data'][0], response[3])
    sys.exit(0)

if __name__ == "__main__":
	main()
