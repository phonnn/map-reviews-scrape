from flask import Flask, request, jsonify
import uuid
import asyncio
import logging
from src.queue.message_queue import RedisQueue
from src.queue.worker import ScrapeWorker
from src.services.scraper import HTMLScraper
from src.services.datastore import SQLite

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
redis = RedisQueue()
scraper = HTMLScraper()
datastore = SQLite()


def generate_request_id():
    return str(uuid.uuid4())


@app.route('/scrape', methods=['POST'])
async def scrape_reviews():
    urls = request.json.get('urls', [])
    request_id = generate_request_id()
    for url in urls:
        await redis.push({'request_id': request_id, 'url': url, 'retry': 0})

    exists = await redis.exists(request_id)
    if not exists:
        await redis.set(request_id, len(urls))

    return jsonify({'request_id': request_id}), 200


@app.route('/status/<request_id>', methods=['GET'])
async def check_status(request_id):
    if await redis.exists(request_id):
        remaining = await redis.get(request_id)
        if remaining == 0:
            await redis.expired(request_id, 900)
            reviews = await datastore.get_reviews(request_id)
            return jsonify({'status': 'completed', 'reviews': reviews}), 200
        else:
            return jsonify({'status': 'in_progress', 'reviews': []}), 200
    else:
        return jsonify({'status': 'not_found'}), 404


async def main():
    logger.info('App starting...')

    worker = ScrapeWorker(redis, scraper, datastore)
    worker_task = asyncio.create_task(worker.start())

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, app.run)
    await worker_task


if __name__ == '__main__':
    asyncio.run(main())
