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

        Label(self, text="Choisir une agence:").grid(row=0, column=0, sticky="w")
        self.agencies = []
        self.agency_var = StringVar()
        self.agency_combobox = ttk.Combobox(self, textvariable=self.agency_var, values=self.agencies, state="readonly")
        self.agency_combobox.bind("<<ComboboxSelected>>", self.check_current_balance)

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

        Label(self, text="Nouvelle agence:").grid(row=4, column=0, sticky="w")
        self.new_agency_var = StringVar()
        self.new_agency_entry = Entry(self, textvariable=self.new_agency_var)
        self.new_agency_entry.grid(row=4, column=1, sticky="ew")

        self.add_agency_button = Button(self, text="Ajouter agence", command=self.create_agency)
        self.add_agency_button.grid(row=4, column=2, padx=5)

        self.result_label = Label(self, text="")
        self.result_label.grid(row=3, column=0, columnspan=3, sticky="w")

        self.fetch_agencies()

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

    def check_current_balance(self, *_):
        try:
            headers = {
                "Authorization": f"Bearer {SECRET}"
            }
            data = {
                "license_id": self.agency_var.get(),
                "amount": 0  # on n'ajoute ni ne retire
            }
            response = requests.post(API_URL, json=data, headers=headers)
            result = response.json()

            if result.get("success"):
                new_balance = result["new_balance"]
                self.result_label.config(text=f"💡 Solde courant: {new_balance} crédits")
            else:
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except Exception as e:
            self.result_label.config(text=f"❌ Erreur réseau: {e}")

    def create_agency(self):
        license_id = self.new_agency_var.get().strip()
        if not license_id:
            self.result_label.config(text="⚠️ Entrez un nom d’agence.")
            return

        headers = {
            "Authorization": f"Bearer {SECRET}"
        }
        data = {"license_id": license_id}

        try:
            response = requests.post("https://license-api-h5um.onrender.com/add_agency", json=data, headers=headers)
            if response.content:
                result = response.json()
            else:
                self.result_label.config(text="❌ Erreur : réponse vide du serveur.")
                return
            if result.get("success"):
                self.result_label.config(text=f"✅ Agence '{license_id}' ajoutée.")
                self.fetch_agencies()
                self.agency_var.set(license_id)
            else:
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except Exception as e:
            self.result_label.config(text=f"❌ Erreur réseau: {e}")

    def fetch_agencies(self):
        try:
            response = requests.get("https://license-api-h5um.onrender.com/list_agencies")
            response.raise_for_status()
            data = response.json()

            # Gère les deux formats possibles
            if isinstance(data, list):
                self.agencies = data
            elif isinstance(data, dict):
                self.agencies = data.get("agencies", [])
            else:
                raise ValueError("Format de réponse inattendu")

            self.agency_combobox['values'] = self.agencies

            if self.agencies:
                self.agency_var.set(self.agencies[0])
                self.check_current_balance()
        except Exception as e:
            self.result_label.config(text=f"❌ Impossible de récupérer les agences: {e}")

