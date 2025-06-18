import requests

url = "https://license-api-h5um.onrender.com/jargonnaire/entry/MonEntree"
headers = {
    "Authorization": "Bearer symcom20250531",
    "Content-Type": "application/json"
}
payload = {
    "explanations": "Voici mes explications.",
    "notes":       "Et mes notes internes."
}

# 1) POST
r = requests.post(url, headers=headers, json=payload)
print("POST", r.status_code)
print("BODY:", repr(r.text))

# 2) GET
r = requests.get(url, headers={"Authorization":"Bearer symcom20250531"})
print("GET", r.status_code)
print("BODY:", repr(r.text))
