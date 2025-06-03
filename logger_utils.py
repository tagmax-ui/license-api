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
                    "timestamp", "agency", "order_number", "raw_words", "weighted_words", "tariff_type", "tariff", "amount"
                ])

    def log(self, agency, order_number="", raw_words=0, weighted_words=0, tariff_type="", tariff=0, amount=0):
        with open(self.file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(), agency, order_number, raw_words, weighted_words, tariff_type, tariff, amount
            ])
