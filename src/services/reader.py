class InputReader:
    def read(self, *args) -> list:
        raise NotImplementedError("Subclasses must implement this method.")


class TXTReader(InputReader):
    def read(self, *args):
        if len(args) != 1 or not isinstance(args[0], str):
            raise ValueError("TXTReader requires a single string argument representing the file path.")

        file_path = args[0]
        with open(file_path, 'r') as input_file:
            return [url.strip() for url in input_file]


class TextReader(InputReader):
    def read(self, *args) -> list:
        if len(args) != 1 or not isinstance(args[0], list):
            raise ValueError("TextReader requires a single text")

        raw_text = args[0]
        url_array = raw_text.split('\n')
        return [url.strip() for url in url_array if isinstance(url, str) and url.strip()]
