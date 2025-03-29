import requests


def use_credits(license_id, units=1000):
    url = "http://127.0.0.1:5000/use_credits"
    payload = {"license_id": license_id, "units": units}
    response = requests.post(url, json=payload)

    if response.ok:
        data = response.json()
        if data["success"]:
            print(f"✅ Remaining credits: {data['remaining']}")
        else:
            print(f"❌ Error: {data['error']}")
    else:
        print(f"❌ Server error: {response.status_code}")


# Example use
if __name__ == "__main__":
    use_credits("agency123")
