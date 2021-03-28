# twitch_online.py
Basic CLI utility to check if a twitch channel is streaming
Mostly useful to integrate with status bars


# Usage

```txt
usage: twitch_online.py [-h] [-a AUTH_FILE] [-t TEMP_FILE] CHANNEL

CLI Utility to check if a twitch channel is streaming

positional arguments:
  CHANNEL               Channel to check

optional arguments:
  -h, --help            show this help message and exit
  -a AUTH_FILE, --auth-file AUTH_FILE
                        File used to store credentials
  -t TEMP_FILE, --temp-file TEMP_FILE
                        File used to store temporary auth token

The credentials file should be a simple yaml file with `client_id` and `client_secret`
variables
```

### Example config
```yaml
client_id: 'asdfhjsadfsadhfhsdfjghskdfg'
client_secret: 'asdfjgsdfhgsdfgjhdsjfgjkgdfgh'
```

# Requirements

* pyyaml
* requests

## Return codes:

0. Stream is live
1. Stream is not live
2. Unhandled Twitch API HTTP status code
128. Failed to parse credentials file
