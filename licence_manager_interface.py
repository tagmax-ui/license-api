import os
import requests
from tkinter import Frame, Label, Entry, Button, StringVar, ttk
from dotenv import load_dotenv

load_dotenv() # Charge le contenu du fichier .env

API_URL = "https://license-api-h5um.onrender.com/modify_credits"
SECRET = os.getenv("ADMIN_PASSWORD")  # Récupère la variable après le chargement

class LicenceManagerFrame(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()

        self.agencies = ["agency123", "agencyXYZ"]

        Label(self, text="Choisir une agence:").grid(row=0, column=0, sticky="w")
        self.agency_var = StringVar(value=self.agencies[0])
        self.agency_combobox = ttk.Combobox(self, textvariable=self.agency_var, values=self.agencies, state="readonly")
        self.agency_combobox.grid(row=0, column=1, sticky="ew")

        Label(self, text="Crédits à ajouter/retirer (en milliers):").grid(row=1, column=0, sticky="w")
        self.amount_var = StringVar()
        self.amount_entry = Entry(self, textvariable=self.amount_var, width=10)
        self.amount_entry.grid(row=1, column=1, sticky="w")
        Label(self, text="000").grid(row=1, column=2, sticky="w")

        self.add_button = Button(self, text="Ajouter", command=self.add_credits)
        self.add_button.grid(row=2, column=0, pady=5)

        self.remove_button = Button(self, text="Retirer", command=self.remove_credits)
        self.remove_button.grid(row=2, column=1, pady=5)

        self.result_label = Label(self, text="")
        self.result_label.grid(row=3, column=0, columnspan=3, sticky="w")

    def update_credits(self, amount):
        try:
            headers = {
                "Authorization": f"Bearer {SECRET}"
            }
            data = {
                "license_id": self.agency_var.get(),
                "amount": amount
            }
            response = requests.post(API_URL, json=data, headers=headers)

            # Vérifie que la réponse contient bien du JSON
            try:
                result = response.json()
            except ValueError:
                self.result_label.config(text=f"❌ Réponse invalide : {response.text}")
                return

            if result.get("success"):
                new_balance = result["new_balance"]
                self.result_label.config(text=f"✅ Nouveau solde: {new_balance} crédits")
            else:
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except Exception as e:
            self.result_label.config(text=f"❌ Erreur réseau: {e}")

    def add_credits(self):
        try:
            amount = int(self.amount_var.get()) * 1000
            self.update_credits(amount)
        except ValueError:
            self.result_label.config(text="⚠️ Entrez un nombre valide.")

    def remove_credits(self):
        try:
            amount = int(self.amount_var.get()) * -1000
            self.update_credits(amount)
        except ValueError:
            self.result_label.config(text="⚠️ Entrez un nombre valide.")
