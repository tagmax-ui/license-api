import csv

def keep_last_n_rows(csv_path, n=10):
    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    header, *data = rows
    new_rows = [header] + data[-n:]
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

# Usage :
keep_last_n_rows('/data/logs.csv', 10)
