import os
from datetime import datetime
import csv

class CSVLogger:
    def __init__(self, file):
        self.file = file
        # S'assurer que le fichier existe avec en-têtes
        if not os.path.exists(self.file):
            with open(self.file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "agency", "action", "item_name", "amount", "word_count", "tariff", "tariff_type"
                ])

    def log(self, agency, action, item_name, amount, word_count=None, tariff=None, tariff_type=None):
        with open(self.file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(), agency, action, item_name, amount, word_count, tariff, tariff_type
            ])
