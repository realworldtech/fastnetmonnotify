# FastNetMon Uiversal Advanced Notification Script

We recently went hunting for a "current" FNM Slack notiification script.

Sadly, there wasn't really any viable solutions around. And ultimatley, we
wanted something that would be "pretty" in slack, but somewhat extensible,
and sensitive to things like API rate limits.

This set of scripts were written in about 4 hours. The code probably isn't beautiful.

They are destributed under the LGPL license at present.

## How it works

The codebase is built to work with two parts:

1. A Docker environment that hosts the integration with Slack (and potentially
other endpoints)

2. A notification script to be used with FastNetMon. The notification script has
minimal Python dependencies, and should work on older systems with Python 2.7
provided the requests library is installed.

## Build instructions

To build the docker environment, ensure you have a working docker-ce install,
and create a .env file based on env.sample. Run docker-compose build and then
docker-compose up.

You'll need a Slack API OAuth Token, which will need the `chat:write` permission.

You'll probably want a channel to post into, e.g. #ddos-notifications

Start your environment with a docker-compose up -d

## Removing Blocks

The interaction includes an implementation to remove blocks. This requires your
notify server to be accessible from the internet. You will need to configure the
SLACK_SIGNING_SECRET and the callback URL in the Slack Application.

Docker will run your server in a "virtual network" and if you are running docker
locally and limiting your API access via iptables you will need to ensure your Docker
service can reach your API server.

Slack allows approx 3 seconds for the server to respond to the API, so if it times out
you will just see a warning icon. 

## Enabling in FastNetMon

Put incoming_notify.py on your server and install python-requests using your
preferred method.

Follow the instructions at https://fastnetmon.com/docs-fnm-advanced/fastnetmon-advanced-json-notify-script-in-python/
and set your incoming_notify.py script to be the script.

&copy; 2021 Real World Technology Solutions Pty Ltd. Written by Andrew Yager. rwts.com.au