from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

def generate_keys():
    """Génère une paire de clés RSA et les retourne (privée, publique)."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key

def save_keys_to_files(private_key, public_key):
    """Sérialise et enregistre les clés dans des fichiers PEM."""
    # Sauvegarder la clé privée (à garder secrète, ne pas la mettre dans le client)
    with open("private_key.pem", "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        )

    # Sauvegarder la clé publique (à inclure côté client)
    with open("public_key.pem", "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )

if __name__ == "__main__":
    # Génère les clés et les sauvegarde dans le dossier courant
    priv, pub = generate_keys()
    save_keys_to_files(priv, pub)
    print("Clés générées et sauvegardées dans private_key.pem et public_key.pem")
