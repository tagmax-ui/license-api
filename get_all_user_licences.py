#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def main():
    # Get the admin token from the environment
    admin_token = os.getenv("ADMIN_PASSWORD")
    if not admin_token:
        print("Error: ADMIN_SECRET environment variable not set.")
        return

    # URL for the download licenses endpoint
    API_URL = "https://license-api-h5um.onrender.com/download_licenses"

    # Set the Authorization header using the admin token
    headers = {
        "Authorization": f"Bearer {admin_token}"
    }

    try:
        response = requests.get(API_URL, headers=headers)
    except Exception as e:
        print("Error connecting to API:", e)
        return

    if response.status_code == 200:
        with open("backup_licenses.json", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Licenses successfully backed up to backup_licenses.json")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    main()
