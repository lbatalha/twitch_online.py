#!/bin/env python3

import os, sys, argparse
import requests, yaml

default_temp_file = '/tmp/twitch_online.token'
default_auth_file = os.path.join(os.environ['XDG_CONFIG_HOME'], 'twitch_online.creds')

parser = argparse.ArgumentParser(description="CLI Utility to check if a twitch channel is streaming", \
        epilog="The credentials file should be a simple yaml file with `client_id` and `client_secret` variables")
parser.add_argument('-a', '--auth-file', default=default_auth_file, help="File used to store credentials")
parser.add_argument('-t', '--temp-file', default=default_temp_file, help="File used to store temporary auth token")
parser.add_argument('CHANNEL', help="Channel to check") 
args = vars(parser.parse_args())
token_file = args['temp_file']

# Init temp token file
if not os.path.isfile(token_file):
    with open(token_file, 'w') as f:
        f.write('')
    # only the calling user should be able to read this
    os.chmod(token_file, 0o600)


# Handle reading config yaml
with open(args['auth_file'], 'r') as f:
    try:
        config = yaml.safe_load(f)
        client_id = config['client_id']
        client_secret = config['client_secret']
        os.chmod(token_file, 0o600)
    except yaml.YAMLError as pe:
        print("Failed to parse credentials file", args['auth_file'])
        print(pe)
        sys.exit(128)


def check_status():
    with open(token_file, 'r') as f:
        auth_token = f.read(256).rstrip('\n')
    auth_headers = {'Authorization': 'Bearer ' + auth_token, \
            'Client-Id': client_id} 
    r = requests.get('https://api.twitch.tv/helix/streams', \
            params={'user_login': args['CHANNEL']}, \
            headers=auth_headers)
    return r

def authenticate():
    auth = requests.post('https://id.twitch.tv/oauth2/token', params={
       		'client_id': client_id,
		'client_secret': client_secret,
		'grant_type': 'client_credentials',
    })

    auth.raise_for_status()

    auth_data = auth.json()
    with open(token_file, 'w') as f:
        f.write(auth_data['access_token'])


def main():
    response = check_status()
    if response.status_code == 401:
        sys.stderr.write("Authentication failed, re-authenticating")
        authenticate()
        response = check_status()
    elif response.status_code == 200:
        if response.json()['data'] and response.json()['data'][0]['type'] == 'live':
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        sys.stderr.write("Unhandled API status code: " + response.status_code)
        sys.stderr.write(response.text)
        sys.exit(2)

if __name__ == "__main__":
	main()
