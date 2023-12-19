import asyncio
import os

from src.reader import InputReader
from src.writer import OutputWriter
from src.scraper import Scraper


class ReviewsProcessor:
    def __init__(self, input_reader: InputReader, data_extractor: Scraper, output_writer: OutputWriter):
        self.input_reader = input_reader
        self.data_extractor = data_extractor
        self.output_writer = output_writer

    def load_checkpoint(self):
        with open('checkpoint.txt', 'r') as file:
            return int(file.read().strip())

    def save_checkpoint(self, index):
        with open('checkpoint.txt', 'w') as file:
            file.write(str(index))

    def reset_checkpoint(self):
        if os.path.exists('checkpoint.txt'):
            os.remove('checkpoint.txt')

    async def run(self, input_file_path, output_file_path):
        urls = self.input_reader.read(input_file_path)
        start_from = self.load_checkpoint() if os.path.exists('checkpoint.txt') else 0

        tasks = [self.data_extractor.extract_reviews(url) for url in urls[start_from:]]
        results = await asyncio.gather(*tasks)

        self.output_writer.write(output_file_path, results)
        self.save_checkpoint(start_from + len(results))

        if start_from + len(results) == len(urls):
            self.reset_checkpoint()
