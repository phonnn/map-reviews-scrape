import csv
import os
from typing import Iterable

from . import OutputWriter
from .utils import convert_data_to_csv


class CSVWriter(OutputWriter):
    @convert_data_to_csv
    def write(self, file_path: str, data: Iterable):
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, 'w', newline='', encoding='utf-8-sig') as output_csv:
            csv_writer = csv.writer(output_csv)
            csv_writer.writerow(['URL', 'Location', 'Reviewer', 'Content'])  # Write header to CSV
            csv_writer.writerows(data)
