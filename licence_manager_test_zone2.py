import os
import requests
from dotenv import load_dotenv

load_dotenv()
url = "https://license-api-h5um.onrender.com/add_agency"
headers = {
    "Authorization": f"Bearer {os.getenv('ADMIN_PASSWORD')}",
    "Content-Type": "application/json"
}
data = {
    "license_id": "symcom"
}

response = requests.post(url, json=data, headers=headers)
print("Status:", response.status_code)
print("Text:", response.text)
