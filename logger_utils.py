import os
from datetime import datetime


class CSVLogger:
    def __init__(self, file="/data/logs.csv"):
        self.file = file
        os.makedirs(os.path.dirname(self.file), exist_ok=True)
        if not os.path.exists(self.file):
            with open(self.file, "w", encoding="utf-8") as f:
                f.write("Date/Heure,Client,Balance Type,Item Name,Amount\n")

    def log(self, client, balance_type, item_name, amount):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.file, "a", encoding="utf-8") as f:
            f.write(f"{now},{client},{balance_type},{item_name},{amount}\n")
