import datetime
import logging
import os
import sys
import pwd
from getpass import getpass

import requests
from garth.exc import GarthHTTPError

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
tokenstore = os.getenv("GARMINTOKENS") or "~/.garminconnect"
tokenstore_base64 = os.getenv(
    "GARMINTOKENS_BASE64") or "~/.garminconnect_base64"
api = None

username = pwd.getpwuid(os.getuid())[0]

computer_dir = os.path.abspath(
    "/run/media/" + username + '/GARMIN/Garmin/Activities')

today = datetime.date.today()


def get_credentials():
    email = input("Login e-mail: ")
    password = getpass("Enter password: ")

    return email, password


def init_api(email, password):
    try:
        print(
            f"Trying to login to Garmin Connect using token data from directory '{
                tokenstore}'...\n"
        )

        garmin = Garmin()
        garmin.login(tokenstore)
    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        print(
            "Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
            f"They will be stored in '{tokenstore}' for future use.\n"
        )
        try:
            if not email or not password:
                email, password = get_credentials()

            garmin = Garmin(email=email, password=password,
                            is_cn=False, prompt_mfa=get_mfa)
            garmin.login()

            garmin.garth.dump(tokenstore)
            print(
                f"OAuth tokens stored in '{
                    tokenstore}' directory for future use. (first method)\n"
            )

            token_base64 = garmin.garth.dumps()
            dir_path = os.path.expanduser(tokenstore_base64)
            with open(dir_path, "w") as token_file:
                token_file.write(token_base64)
            print(
                f"OAuth tokens encoded as base64 string and saved to '{
                    dir_path}' file for future use. (second method)\n"
            )
        except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError, requests.exceptions.HTTPError) as err:
            logger.error(err)
            return None
    return garmin


def get_mfa():
    return input("MFA one-time code: ")


api = init_api(email, password)

last_cycling_activity = api.get_activities_by_date(
    datetime.date.today()-datetime.timedelta(days=128),
    datetime.date.today(),
    "cycling"
)[0]
# print(last_cycling_activity)
last_cycling_date = last_cycling_activity['startTimeLocal']
last_cycling_date = datetime.datetime.strptime(
    last_cycling_date, '%Y-%m-%d %H:%M:%S')

new_activities = []

if not os.path.exists(computer_dir):
    sys.stderr.buffer.write(b'Bike computer directory not valid\n')
    sys.exit(-1)

for file in os.listdir(computer_dir):
    clean_filename = file.strip('.fit')
    activity_date = datetime.datetime.strptime(
        clean_filename, '%Y-%m-%d-%H-%M-%S')
    if activity_date > last_cycling_date:
        new_activities.append(file)

print(new_activities)

activity_upload_responses = []

for file in new_activities:
    full_path = os.path.join(computer_dir, file)
    resp = api.upload_activity(full_path)
    activity_upload_responses.append(resp)

print(activity_upload_responses)

