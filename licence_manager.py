from tkinter import Tk, Frame, Label, Entry, Button, StringVar, ttk, LabelFrame
import os
import requests
from tkinter import messagebox
from dotenv import load_dotenv
from db_logger import DBLogger
import json
import math

load_dotenv()

API_URL_USE_WORDS = "https://license-api-h5um.onrender.com/use_words"
API_URL_REGISTER_PAYMENT = "https://license-api-h5um.onrender.com/register_payment"
API_URL_ADD_AGENCY = "https://license-api-h5um.onrender.com/add_agency"
API_URL_LIST_AGENCIES = "https://license-api-h5um.onrender.com/list_agencies"
API_URL_GET_DEBT = "https://license-api-h5um.onrender.com/get_debt"
API_URL_DOWNLOAD = "https://license-api-h5um.onrender.com/download_logs"
SECRET = os.getenv("ADMIN_PASSWORD")

tariff_types_path = os.getenv("TARIFF_TYPES_PATH")
if tariff_types_path and os.path.exists(tariff_types_path):
    with open(tariff_types_path, encoding="utf-8") as f:
        TARIFF_TYPES = json.load(f)
else:
    TARIFF_TYPES = {}


db_logger = DBLogger()






class LicenceManagerFrame(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack(padx=10, pady=10)

        self.agency_var = StringVar()
        self.weighted_word_count_var = StringVar()
        self.tariff_type_var = StringVar(value="weighter")
        self.item_name_var = StringVar()
        self.payment_var = StringVar()
        self.credit_var = StringVar()
        self.new_agency_var = StringVar()
        # self.weighter_tariff_var = StringVar()
        # self.valuechecker_tariff_var = StringVar()
        # self.terminology_tariff_var = StringVar()
        # self.pretranslation_tariff_var = StringVar()
        self.tariff_vars = {}
        for key in TARIFF_TYPES:
            self.tariff_vars[key] = StringVar()


        self.result_label = Label(self, text="Système de facturation post-payé (DETTE)", fg="red")
        self.result_label.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))
        self.tariff_display_to_key = {v: k for k, v in TARIFF_TYPES.items()}
        self.greeting_var = StringVar()
        self.disabled_items_var = StringVar()

        self.frame_agency = LabelFrame(master=self)
        self.frame_agency.grid(row=1, column=0, sticky="ew", columnspan=12)

        # 1. Agency choice
        Label(self.frame_agency, text="Agence:").grid(row=1, column=0, sticky="w")
        self.agency_combobox = ttk.Combobox(self.frame_agency, textvariable=self.agency_var, values=[], state="readonly")
        self.agency_combobox.bind("<<ComboboxSelected>>", self.refresh_debt_display)
        self.agency_combobox.grid(row=1, column=1, sticky="ew")
        Button(self.frame_agency, text="Rafraîchir agences", command=self.fetch_agencies).grid(row=1, column=3)

        Label(self.frame_agency, text="Message d’accueil :").grid(row=2, column=0, sticky="w", pady=(10, 0))
        Entry(self.frame_agency, textvariable=self.greeting_var, width=200).grid(row=2, column=1,
                                                                                 sticky="ew", pady=(10, 0))
        Label(self.frame_agency, text="Objets à désactiver (virgules) :").grid(row=3, column=0, sticky="w",
                                                                               pady=(10, 0))
        Entry(self.frame_agency, textvariable=self.disabled_items_var, width=200).grid(row=3, column=1,
                                                                                       sticky="ew", pady=(10, 0))

        self.frame_tariffs = LabelFrame(master=self, text="Tarification")
        self.frame_tariffs.grid(row=2, column=1, columnspan=2, sticky="ew")

        COLS = math.ceil(len(TARIFF_TYPES) / 10)  # Pour exactement 3 lignes

        for i, (key, label) in enumerate(TARIFF_TYPES.items()):
            row = 7 + i // COLS
            col = 2 * (i % COLS)
            Label(self.frame_tariffs, text=label).grid(row=row, column=col, sticky="w")
            Entry(self.frame_tariffs, textvariable=self.tariff_vars[key], width=8).grid(row=row, column=col + 1,
                                                                                         sticky="w")

        # Le bouton Enregistrer, mets-le à la suite, par exemple :
        Button(self.frame_tariffs, text="Enregistrer", command=self.update_tariffs).grid(
            row=7 + math.ceil(len(TARIFF_TYPES) / COLS), column=0, columnspan=2 * COLS, pady=(8, 0)
        )

        # 2. Current Debt
        Label(self, text="Dette actuelle:").grid(row=2, column=0, sticky="w")
        self.debt_label = Label(self, text="0.00 $")
        self.debt_label.grid(row=3, column=1, sticky="w")
        Button(self, text="Rafraîchir dette", command=self.refresh_debt_display).grid(row=2, column=3)

        # 3. Add work (increase debt)
        Label(self, text="Ajouter du travail").grid(row=3, column=0, sticky="w", pady=(10, 0))
        Label(self, text="Mots:").grid(row=4, column=0, sticky="w")
        Entry(self, textvariable=self.weighted_word_count_var, width=10).grid(row=4, column=1, sticky="w")
        Label(self, text="Service:").grid(row=4, column=2, sticky="w")
        self.tariff_type_var = StringVar()

        self.tariff_combobox = ttk.Combobox(
            self,
            textvariable=self.tariff_type_var,
            values=list(TARIFF_TYPES.values()),  # affiche seulement les labels FR
            state="readonly",
            width=15)

        self.tariff_combobox.grid(row=4, column=3, sticky="w")
        Label(self, text="Description:").grid(row=4, column=4, sticky="w")
        Entry(self, textvariable=self.item_name_var, width=15).grid(row=4, column=5, sticky="w")
        label = self.tariff_type_var.get()
        if not label:
            # Prendre la première valeur par défaut
            label = list(self.tariff_display_to_key.keys())[0]
        tariff_key = self.tariff_display_to_key[label]
        Button(self, text="Ajouter à la dette", command=self.add_work).grid(row=4, column=6, padx=(10, 0))

        # 4. Register payment (reduce debt)
        Label(self, text="Paiement reçu ($)").grid(row=5, column=0, sticky="w", pady=(10, 0))
        Entry(self, textvariable=self.payment_var, width=10).grid(row=5, column=1, sticky="w")
        Button(self, text="Enregistrer paiement", command=self.register_payment).grid(row=5, column=2, padx=(10, 0),
                                                                                      pady=(10, 0))

        # 5. Add agency
        Label(self, text="Nouvelle agence").grid(row=6, column=0, sticky="w", pady=(20, 0))
        Entry(self, textvariable=self.new_agency_var, width=20).grid(row=6, column=1, columnspan=2, sticky="ew",
                                                                     pady=(20, 0))
        Button(self, text="Ajouter agence", command=self.create_agency).grid(row=6, column=3, pady=(20, 0))
        Button(self, text="Supprimer agence", command=self.delete_agency, fg="red").grid(row=6, column=4, pady=(20, 0))

        Button(self, text="Télécharger les transactions", command=self.download_transactions).grid(row=7, column=3, pady=(20, 0))
        Button(self, text="Réinitialiser logs", command=self.reset_logs, fg="red").grid(row=7, column=4, pady=(20, 0))

        Label(self, text="Début (timestamp):").grid(row=8, column=0, sticky="w")
        self.start_timestamp_var = StringVar()
        Entry(self, textvariable=self.start_timestamp_var, width=15).grid(row=8, column=1, sticky="w")

        Label(self, text="Fin (timestamp):").grid(row=8, column=2, sticky="w")
        self.end_timestamp_var = StringVar()
        Entry(self, textvariable=self.end_timestamp_var, width=15).grid(row=8, column=3, sticky="w")

        Button(self, text="Supprimer transactions", command=lambda: self.delete_transactions_by_date(
            int(self.start_timestamp_var.get()), int(self.end_timestamp_var.get()))
               ).grid(row=8, column=4, pady=(10, 0))

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.fetch_agencies()

    def fetch_agencies(self):
        try:
            response = requests.get(API_URL_LIST_AGENCIES)
            response.raise_for_status()
            result = response.json()
            self.agencies = result if isinstance(result, list) else result.get("agencies", [])
            self.agency_combobox['values'] = self.agencies
            if self.agencies:
                self.agency_var.set(self.agencies[0])
                self.refresh_debt_display()
        except Exception as e:
            self.result_label.config(text=f"❌ Impossible de récupérer les agences: {e}")

    def update_tariffs(self):
        agency_name = self.agency_var.get()
        if not agency_name:
            self.result_label.config(text="⚠️ Sélectionnez une agence pour modifier ses tarifs.")
            return

        data = {"agency_name": agency_name}
        data["greeting"] = self.greeting_var.get()
        data["disabled_items"] = self.disabled_items_var.get()
        print("Le data avant l'envoi: ", data)
        try:
            # Boucle sur tous les types de tarifs connus
            for key in TARIFF_TYPES:
                value_str = self.tariff_vars[key].get()
                data[key] = float(value_str)
        except ValueError:
            data[key] = 0.0

        headers = {"Authorization": f"Bearer {SECRET}"}


        try:
            response = requests.post(
                "https://license-api-h5um.onrender.com/update_tariffs",
                json=data,
                headers=headers
            )
            result = response.json()
            if result.get("success"):
                self.result_label.config(text="✅ Tarifs mis à jour.")
            else:
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except Exception as e:
            self.result_label.config(text=f"❌ Erreur réseau: {e}")

    def refresh_debt_display(self, *_):
        agency_name = self.agency_var.get()
        if not agency_name:
            self.debt_label.config(text="---")
            return
        try:
            headers = {"Authorization": f"Bearer {agency_name}"}
            response = requests.post(API_URL_GET_DEBT, headers=headers)
            result = response.json()
            print("result dans refresh_debt_display:", result)
            if result.get("success"):
                debt = result.get("debt", 0)
                self.debt_label.config(text=f"{debt:.2f} $")
                tariffs = result.get("tariffs", {})
                # DRY : boucle sur tous les types de tarif connus
                for key in TARIFF_TYPES:
                    value = tariffs.get(key, "")
                    if isinstance(value, float) or isinstance(value, int):
                        value = f"{value:.5f}".rstrip('0').rstrip('.') if '.' in f"{value:.5f}" else str(value)
                    self.tariff_vars[key].set(value)
                self.result_label.config(text="")
                greeting = result.get("greeting", "")
                self.greeting_var.set(greeting)
                disabled_items = result.get("disabled_items", "")
                self.disabled_items_var.set(disabled_items)
            else:
                self.debt_label.config(text="Erreur")
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except Exception as e:
            self.debt_label.config(text="Erreur")
            self.result_label.config(text=f"❌ Erreur réseau: {e}")

    def add_work(self):
        try:
            agency = self.agency_var.get()
            word_count = int(self.weighted_word_count_var.get())
            tariff_type = self.tariff_display_to_key[self.tariff_type_var.get()]
            item_name = self.item_name_var.get()
            if not agency or word_count <= 0 or not tariff_type:
                self.result_label.config(text="⚠️ Remplir tous les champs travail.")
                return
            headers = {"Authorization": f"Bearer {agency}"}
            data = {
                "word_count": word_count,
                "tariff_type": tariff_type,
                "item_name": item_name
            }
            response = requests.post(API_URL_USE_WORDS, json=data, headers=headers)
            result = response.json()
            if result.get("success"):
                self.result_label.config(text=f"✅ Travail ajouté. Nouvelle dette : {result.get('new_debt'):.2f} $")
                self.refresh_debt_display()
                db_logger.log(agency=agency,
                               item_name=item_name,
                               weighted_words=word_count,
                               tariff_type=tariff_type)
            else:
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except ValueError:
            self.result_label.config(text="⚠️ Nombre de mots invalide.")
        except Exception as e:
            self.result_label.config(text=f"❌ Erreur réseau: {e}, {response}")

    def register_payment(self):
        try:
            agency = self.agency_var.get()
            amount = float(self.payment_var.get())
            if not agency or amount <= 0:
                self.result_label.config(text="⚠️ Entrez un montant de paiement valide.")
                return
            headers = {"Authorization": f"Bearer {SECRET}"}
            data = {"agency_name": agency, "amount": amount}
            response = requests.post(API_URL_REGISTER_PAYMENT, json=data, headers=headers)
            result = response.json()
            if result.get("success"):
                self.result_label.config(text=f"✅ Paiement enregistré. Nouvelle dette : {result.get('new_debt'):.2f} $")
                self.refresh_debt_display()
                db_logger.log(agency, "payment", "", -amount)
            else:
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except ValueError:
            self.result_label.config(text="⚠️ Montant de paiement invalide.")
        except Exception as e:
            self.result_label.config(text=f"❌ Erreur réseau: {e}, {response}")

    def create_agency(self):
        agency_name = self.new_agency_var.get().strip()
        if not agency_name:
            self.result_label.config(text="⚠️ Entrez un nom d’agence.")
            return
        headers = {"Authorization": f"Bearer {SECRET}"}

        # DRY : on met tous les tarifs à 1
        data = {"agency_name": agency_name}
        for key in TARIFF_TYPES:
            data[key] = 1

        try:
            response = requests.post(API_URL_ADD_AGENCY, json=data, headers=headers)
            result = response.json()
            if result.get("success"):
                self.result_label.config(text=f"✅ Agence '{agency_name}' ajoutée.")
                self.fetch_agencies()
                self.agency_var.set(agency_name)
            else:
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except Exception as e:
            self.result_label.config(text=f"❌ Erreur réseau: {e}")

    def delete_agency(self):
        agency_name = self.agency_var.get()
        if not agency_name:
            self.result_label.config(text="⚠️ Sélectionnez une agence à supprimer.")
            return
        from tkinter import messagebox
        if not messagebox.askyesno("Confirmer", f"Supprimer l’agence « {agency_name} » ?"):
            return
        headers = {"Authorization": f"Bearer {SECRET}"}
        data = {"agency_name": agency_name}
        try:
            response = requests.post("https://license-api-h5um.onrender.com/delete_agency", json=data, headers=headers)
            result = response.json()
            if result.get("success"):
                self.result_label.config(text=f"✅ Agence « {agency_name} » supprimée.")
                self.fetch_agencies()
            else:
                self.result_label.config(text=f"❌ Erreur: {result.get('error')}")
        except Exception as e:
            self.result_label.config(text=f"❌ Erreur réseau: {e}, {response}")

    def download_transactions(self):

        headers = {
            "Authorization": f"Bearer {SECRET}"
        }

        try:
            response = requests.get(API_URL_DOWNLOAD, headers=headers)
        except Exception as e:
            print("Erreur lors de la connexion à l'API :", e)
            return

        if response.status_code == 200:
            # Sauvegarde du contenu dans un fichier local
            with open("transactions.csv", "wb") as file:
                file.write(response.content)
            message = "Les transactions ont bien été téléchargées sous le nom 'transactions.csv'."
            print(message)
            messagebox.showinfo(title="Gestionnaire de licences", message=message)
        else:
            message = f"Erreur {response.status_code} : {response.text}"
            print(message)
            messagebox.showerror(title="Gestionnaire de licences", message=message)

    def reset_logs(self):
        # Première confirmation (soft warning)
        if not messagebox.askyesno("Attention", "⚠️ Tu es sur le point d’effacer complètement les logs. Continuer ?"):
            return
        # Deuxième confirmation (vraiment sûr)
        if not messagebox.askyesno("Confirmation ultime",
                                   "🛑 Es-tu VRAIMENT SÛR de vouloir effacer les logs ? Cette action est irréversible."):
            return

        url = "https://license-api-h5um.onrender.com/reset_logs"
        headers = {"Authorization": f"Bearer {SECRET}"}
        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    messagebox.showinfo("Logs", "✅ Les logs ont été réinitialisés côté serveur.")
                else:
                    messagebox.showerror("Erreur", f"Erreur serveur: {data.get('error')}")
            else:
                messagebox.showerror("Erreur", f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            messagebox.showerror("Erreur réseau", f"Erreur de connexion: {e}")

    def delete_transactions_by_date(self, start_timestamp, end_timestamp):
        headers = {"Authorization": f"Bearer {SECRET}"}
        data = {"start_timestamp": start_timestamp, "end_timestamp": end_timestamp}
        try:
            response = requests.post("https://license-api-h5um.onrender.com/delete_transactions", json=data, headers=headers)
            result = response.json()
            if result.get("success"):
                messagebox.showinfo("Suppression", "✅ Transactions supprimées.")
            else:
                messagebox.showerror("Erreur", f"Erreur: {result.get('error')}")
        except Exception as e:
            messagebox.showerror("Erreur réseau", f"Erreur de connexion: {e}")



if __name__ == "__main__":
    root = Tk()
    root.title("Gestion facturation et dette des agences")
    frame = LicenceManagerFrame(master=root)
    root.mainloop()
