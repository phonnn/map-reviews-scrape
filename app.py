from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import asyncio
import logging
from src.queue.message_queue import RedisQueue
from src.queue.worker import ScrapeWorker, Publisher
from src.services.email_sender import EmailSender
from src.services.scraper import HTMLScraper
from src.services.datastore import SQLite
from dotenv import load_dotenv
import os

from src.services.writer import CSVWriter

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()
app = Flask(__name__)
CORS(app)
redis = RedisQueue()
scraper = HTMLScraper()
datastore = SQLite()


def generate_request_id():
    return str(uuid.uuid4())


@app.route('/scrape', methods=['POST'])
async def scrape_reviews():
    urls = request.json.get('urls', [])
    email = request.json.get('email', '')
    request_id = generate_request_id()
    for url in urls:
        await redis.push({'request_id': request_id, 'url': url, 'retry': 0}, 'scrape')

    exists = await redis.exists(request_id)
    if not exists:
        await redis.set(request_id, {'email': email, 'amount': len(urls), 'process': 0})

    return jsonify({'request_id': request_id}), 200


# @app.route('/status/<request_id>', methods=['GET'])
# async def check_status(request_id):
#     if await redis.exists(request_id):
#         remaining = await redis.get(request_id)
#         if remaining <= 0:
#             await redis.expired(request_id, 900)
#             reviews = await datastore.get_reviews(request_id)
#             return jsonify({'status': 'completed', 'reviews': reviews}), 200
#         else:
#             return jsonify({'status': 'in_progress', 'reviews': []}), 200
#     else:
#         return jsonify({'status': 'not_found'}), 404


async def main():
    logger.info('App starting...')
    await datastore.connect()

    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT'))
    email = os.getenv('SENDER_EMAIL')
    password = os.getenv('EMAIL_PASSWORD')
    email_sender = EmailSender(smtp_server, smtp_port, email, password)
    logger.info('Connect to SMTP server...')
    await email_sender.connect()

    worker = ScrapeWorker(redis, scraper, datastore)
    worker_task = asyncio.create_task(worker.start())

    writer = CSVWriter()
    publisher = Publisher(redis, datastore, writer, email_sender)
    publisher_task = asyncio.create_task(publisher.start())

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, app.run)

    await worker_task
    await publisher_task


if __name__ == '__main__':
    asyncio.run(main())
