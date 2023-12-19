import csv


class OutputWriter:
    def write(self, file_path: str, data):
        raise NotImplementedError("Subclasses must implement this method.")


class CSVWriter(OutputWriter):
    def write(self, file_path, data):
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as output_csv:
            csv_writer = csv.writer(output_csv)
            csv_writer.writerow(['URL', 'Location', 'Reviewer', 'Content'])  # Write header to CSV
            csv_writer.writerows(data)

        print(f"Output written to {file_path}")