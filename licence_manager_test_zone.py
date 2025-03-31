import requests

url = "https://license-api-h5um.onrender.com/modify_credits"
headers = {
    "Authorization": "Bearer TOPSECRET123",
    "Content-Type": "application/json"
}
data = {
    "license_id": "agency123",
    "amount": 3000
}

response = requests.post(url, json=data, headers=headers)

print("Status Code:", response.status_code)
print("Response:", response.text)
