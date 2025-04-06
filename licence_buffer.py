import json
import os
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization

def generate_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key


# Path to the cached file (you might choose a less obvious location)
CACHE_FILE = "buffer_cache.json"


def save_buffer(buffer_date: datetime, private_key):
    """
    Saves the buffer period date along with a digital signature.
    The private_key is used to sign the JSON representation of the data.
    """
    # Prepare data
    data = {
        "buffer": buffer_date.isoformat()
    }
    # Convert data to a canonical JSON format (sorted keys) and encode to bytes
    json_data = json.dumps(data, sort_keys=True).encode('utf-8')

    # Sign the data using the private key
    signature = private_key.sign(
        json_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    # Store the data and signature (signature is hex-encoded for storage)
    cache = {
        "data": data,
        "signature": signature.hex()
    }

    # Write the cache to file
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)
    print("Grace period date saved securely.")


def load_and_verify_buffer(public_key):
    """
    Loads the buffer period date and verifies its integrity.
    If the data has been tampered with, verification will fail.
    """
    if not os.path.exists(CACHE_FILE):
        raise FileNotFoundError("Cache file not found.")

    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)

    data = cache.get("data")
    signature_hex = cache.get("signature")
    if not data or not signature_hex:
        raise ValueError("Cache file is corrupted or incomplete.")

    # Recreate the original JSON data (canonical format) and decode the signature
    json_data = json.dumps(data, sort_keys=True).encode('utf-8')
    signature = bytes.fromhex(signature_hex)

    try:
        # Verify the signature using the public key
        public_key.verify(
            signature,
            json_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        # Signature is valid; parse and return the buffer period date
        buffer_date = datetime.fromisoformat(data["buffer"])
        return buffer_date
    except Exception as e:
        raise ValueError("Data verification failed. The file may have been tampered with.") from e


# Example usage:
if __name__ == "__main__":
    # Generate keys for demonstration (in production, generate keys once and store securely)
    private_key, public_key = generate_keys()

    # Set a buffer period date (for example, 7 days from now)
    buffer_date = datetime.utcnow().replace(microsecond=0)
    save_buffer(buffer_date, private_key)

    # Later, load and verify the buffer period date
    try:
        verified_date = load_and_verify_buffer(public_key)
        print("Verified buffer period date:", verified_date)
    except Exception as err:
        print("Verification error:", err)
