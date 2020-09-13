import csv
from typing import List


class CSVWriter:

    def __init__(self, csv_path: str, fields: List[str]):
        self.file_path = csv_path
        self.fields = fields

    def write_row(self, row_data: dict):
        with open(self.file_path, "a") as f:

            writer = csv.DictWriter(f, self.fields)
            writer.writerow(row_data)