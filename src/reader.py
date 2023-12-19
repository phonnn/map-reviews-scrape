class InputReader:
    def read(self, file_path: str) -> list:
        raise NotImplementedError("Subclasses must implement this method.")


class TXTReader(InputReader):
    def read(self, file_path):
        with open(file_path, 'r') as input_file:
            return [url.strip() for url in input_file]
