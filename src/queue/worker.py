import logging
from abc import ABC, abstractmethod
from .message_queue import MQueue
from ..services.scraper import Scraper
from ..services.datastore import DataStore

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
            item = await self.queue.pop()
            await self.process_item(item)

    async def process_item(self, item):
        request_id = item['request_id']
        url = item['url']
        retry = item['retry']

        if retry >= 3:
            review = [url, 'Error', 'Error', 'Error']
            await self.save_to_db(request_id, url, review)
            return

        try:
            review = await self.scraper.extract_reviews(url)
            await self.save_to_db(request_id, url, review)
            await self.queue.decr(request_id)

        except Exception as e:
            logger.error(f'{e}')
            item['retry'] += 1
            await self.queue.push(item)

    async def save_to_db(self, request_id:str, url:str, review:list):
        await self.db.save_review(request_id, url, review[1], review[2], review[3])
