import csv


class OutputWriter:
    def write(self, file_path: str, data):
        raise NotImplementedError("Subclasses must implement this method.")


class CSVWriter(OutputWriter):
    def write(self, *args):
        if len(args) != 1 or not isinstance(args[0], str):
            raise ValueError("CSVWriter requires 2 arguments")

        file_path = args[0]
        data = args[0]
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as output_csv:
            csv_writer = csv.writer(output_csv)
            csv_writer.writerow(['URL', 'Location', 'Reviewer', 'Content'])  # Write header to CSV
            csv_writer.writerows(data)

        print(f"Output written to {file_path}")