import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Callable

from .message_queue import MQueue
from ..services.email_sender import EmailSender
from ..services.scraper import Scraper
from ..services.datastore import DataStore
from ..services.writer import OutputWriter

logger = logging.getLogger(__name__)


class Worker(ABC):
    @abstractmethod
    async def start(self):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def process_item(self, item):
        raise NotImplementedError("Subclasses must implement this method.")


class ScrapeWorker(Worker):
    def __init__(self, queue: MQueue, scraper: Scraper, db: DataStore):
        self.queue = queue
        self.scraper = scraper
        self.db = db

    async def start(self):
        while True:
            item = await self.queue.pop('scrape')
            if item is not None:
                await self.process_item(item)

            await asyncio.sleep(0)

    async def process_item(self, item):
        request_id = item['request_id']
        url = item['url']
        retry = item['retry']
        review = None
        _need_save = True

        try:
            _return = False
            if retry >= 3:
                review = [url, 'Error', 'Error', 'Error']
                _need_save = False
                _return = True

            if not _return:
                check = await self.check_url(url)
                if check['status']:
                    review = check['review']
                    _return = True

            if not _return:
                review = await self.scraper.extract_reviews(url)

            logger.info(f'Fetch url OK: {url} - {review}')
        except Exception as e:
            print(e)
            logger.info(f'Fetch url error: {url} - {e}')
            item['retry'] += 1
            await self.queue.push(item, 'scrape')

        if review is not None and _need_save:
            await self.save(request_id, review)

        await self.queue.push({'request_id': request_id}, 'notify')

    async def save(self, request_id: str, review: list):
        await self.db.save_review(request_id, review[0], review[1], review[2], review[3])

    async def check_url(self, url: str):
        reviews = await self.db.finds('Review', url=url)
        now = datetime.now()

        if len(reviews) > 0:
            last_update = datetime.strptime(reviews[0][1], '%Y-%m-%d %H:%M:%S')
            if now - last_update > timedelta(minutes=30):
                return {'status': True, 'review': [url, reviews[0][4], reviews[0][5], reviews[0][6]]}

        return {'status': False, 'review': None}


class Publisher(Worker):
    def __init__(self, queue: MQueue, db: DataStore, writer: OutputWriter = None, sender: EmailSender=None):
        self.queue = queue
        self.writer = writer
        self.db = db
        self.sender = sender

    async def start(self):
        while True:
            item = await self.queue.pop('notify')
            if item is not None:
                await self.process_item(item)

            await asyncio.sleep(0)

    async def process_item(self, item):
        request_id = item.get('request_id', '')
        request = await self.queue.get(request_id)
        request = json.loads(request)

        logger.info(f'Try publish to: {request['email']}')

        process = request['process'] + 1
        if process >= request['amount']:
            await self.queue.expired(request_id, 900)
            reviews = await self.db.get_reviews(request_id)

            email = request['email']
            file_path = f'./temp/{email}.csv'
            if self.writer is not None:
                self.writer.write(file_path, reviews)

            # await self.sender.send_email(email, 'Test Subject', '<h1>Test Body</h1>', file_path)
            asyncio.create_task(self.sender.send_email(email, 'Test Subject', '<h1>Test Body</h1>', file_path))

            await self.clear()

        request['process'] = process
        await self.queue.set(request_id, request)

    async def clear(self):
        await self.db.delete_reviews()
