import argparse
import asyncio

from src.services.reader import TXTReader
from src.services.writer import CSVWriter
from src.services.scraper import HTMLScraper
from src.services.processor import ReviewsProcessor

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process reviews from input URLs and write to CSV.')
    parser.add_argument('--input', '-i', help='Input file path')
    parser.add_argument('--output', '-o', help='Output file path', default='output_reviews.csv')
    args = parser.parse_args()

    input_file_path = args.input
    output_file_path = args.output

    web_scraper = HTMLScraper()
    input_reader = TXTReader()
    output_writer = CSVWriter()

    review_processor = ReviewsProcessor(input_reader, web_scraper, output_writer)
    try:
        asyncio.run(review_processor.run(input_file_path, output_file_path))
    except Exception as e:
        print(f"Error occurred: {str(e)}. Attempting to resume from the last successful point.")
        asyncio.run(review_processor.run(input_file_path, output_file_path))
