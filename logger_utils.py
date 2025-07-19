import os
from datetime import datetime
from datetime import timezone
import csv
import time

class CSVLogger:
    def __init__(self, file):
        self.file = file
        # S'assurer que le fichier existe avec en-têtes
        if not os.path.exists(self.file):
            with open(self.file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "client", "timestamp", "iso_datetime", "service", "order", "user",
                    "filename", "words", "tariff", "amount", "balance"
                ])

    def log(
            self,
            client,
            service,
            order="",
            user="",
            filename="",
            words=0,
            tariff=0,
            amount=0,
            balance=0
    ):
        unix_timestamp = int(time.time())
        iso_datetime = datetime.now(timezone.utc).astimezone().isoformat()
        with open(self.file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                client,
                unix_timestamp,
                iso_datetime,
                service,
                order,
                user,
                filename,
                words,
                tariff,
                amount,
                balance
            ])


def keep_last_n_rows(csv_path, n=10):
    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    header, *data = rows
    new_rows = [header] + data[-n:]
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

def reset_csv(file_path):
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "client", "timestamp", "service", "order", "user",
            "filename", "words", "tariff", "amount", "balance"
        ])