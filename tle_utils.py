# -*- coding: utf-8 -*-
"""
Created on Sat Aug  3 17:25:33 2024

@author: kslawek
"""

import os
import requests
from datetime import datetime

# Define the URL for downloading TLE data
TLE_URL = 'https://celestrak.org/NORAD/elements/weather.txt'  # Example URL, you might need to update this

# Define the path where TLE data will be saved
TLE_FILE_PATH = 'weather.txt'
def download_tle_if_necessary(update_days):
    """
    Downloads the TLE data if it doesn't already exist or if it's outdated.
    """
    # Check if the TLE file already exists
    if not os.path.exists(TLE_FILE_PATH):
        print("TLE file not found. Downloading...")
        download_tle()
    else:
        # Check the file's modification time
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(TLE_FILE_PATH))
        current_time = datetime.now()
        # Update file if it's older than 1 day
        if (current_time - file_mod_time).days >= update_days:
            print("TLE file is outdated. Downloading new one...")
            download_tle()
        else:
            print("TLE file is up-to-date.")

def download_tle():
    """
    Downloads the TLE data from the specified URL and saves it to the TLE_FILE_PATH.
    """
    try:
        response = requests.get(TLE_URL)
        response.raise_for_status()
        with open(TLE_FILE_PATH, 'w') as file:
            file.write(response.text)
        print("TLE data downloaded successfully.")
    except requests.RequestException as e:
        print(f"Error downloading TLE data: {e}")
