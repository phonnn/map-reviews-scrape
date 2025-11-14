import asyncio
import logging
import os
from datetime import datetime, timedelta

from flask.ctx import AppContext
from flask_mail import Message, Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import distinct

from src.datastore.models import Review, Progress, ProgressStatus, Request
from src.datastore.utils import bulk_insert_or_update
from src.scraper import IScraper
from src.writer import OutputWriter
from . import MQueue, Worker
from src.utils import send_email_with_attachment

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ScrapeWorker(Worker):
    def __init__(self, queue: MQueue, scraper: IScraper, db: SQLAlchemy):
        self.queue = queue
        self.scraper = scraper
        self.db = db
        self.pending_urls = set()
        self.last_run = set()
        self.last_gather = datetime.now()

    async def listen(self, context):
        with context:
            while True:
                try:
                    item = await self.queue.pop('scrape')
                    await self.on_data(item)
                except Exception as e:
                    logger.debug(f'Worker error: {e}')

                await asyncio.sleep(0)

    async def on_data(self, item):
        if item is not None:
            logger.info(f'Add scrape task: {item}')
            # add new url into task queue
            self.add_task(item)

        # a priority mechanism
        for url in self.priority_item():
            if url not in self.pending_urls:
                self.pending_urls.add(url)
        # do scrape task
        await self.do_task()
        await asyncio.sleep(0)

    async def start(self, item):
        # item should be {'url': url, 'request_id': 0}
        await self.queue.push(item, 'scrape')

    def add_task(self, item: dict):
        url = item.get('url', '')
        if url:
            self.pending_urls.add(url)

    def pop_items(self, n):
        items = set()
        for _ in range(min(len(self.pending_urls), n)):
            item = self.pending_urls.pop()
            items.add(item)
        return items

    def priority_item(self):
        priority_task = self.db.session.query(Progress).filter(
            Progress.status == ProgressStatus.PENDING,
            datetime.now() - Progress.created_at > timedelta(minutes=5)
        )

        return set([record.url for record in priority_task])

    async def do_task(self):
        _now = datetime.now()
        if _now - self.last_gather < timedelta(milliseconds=500):
            return

        cond1 = len(self.pending_urls) >= 50
        cond2 = (_now - self.last_gather > timedelta(seconds=10)) and len(self.pending_urls) > 0
        if cond1 or cond2:
            self.last_gather = datetime.now()
            urls_to_process = self.pop_items(50)
            tasks = [self.scraper.scrape(url) for url in urls_to_process]
            results = await asyncio.gather(*tasks)
            bulk_insert_or_update(self.db, list(results))

            # Perform the update operation
            updated_record = self.db.session.query(Progress).filter(Progress.url.in_(urls_to_process)).all()

            for record in updated_record:
                record.status = ProgressStatus.NOTIFYING

            self.db.session.commit()

class Publisher(Worker):
    def __init__(self, queue: MQueue, db: SQLAlchemy, writer: OutputWriter = None, sender: Mail = None):
        self.queue = queue
        self.writer = writer
        self.db = db
        self.sender = sender

    async def listen(self, context: AppContext):
        with context:
            while True:
                try:
                    self.notify()
                except Exception as e:
                    logger.debug(f'Publisher error: {e}')


                await asyncio.sleep(0)

    async def start(self, item: dict):
        pass

    def registerMailService(self, mailService: Mail = None):
        self.sender = mailService

    def get_notify(self):
        query = self.db.session.query(distinct(Progress.request_id)).filter(
            Progress.status == ProgressStatus.NOTIFYING)

        for request_id_tuple in query.yield_per(100):  # Adjust the batch size as needed
            yield request_id_tuple[0]

    def notify(self):
        for request_id in self.get_notify():
            progress = self.db.session.query(Progress).filter_by(request_id=request_id).all()

            pending = any(record.status == ProgressStatus.PENDING for record in progress)
            if not pending:
                if self.writer is not None:
                    urls = [record.url for record in progress]
                    reviews = self.db.session.query(Review).filter(Review.url.in_(urls)).all()
                    file_path = f'./temp/{request_id}.csv'
                    self.writer.write(file_path, reviews)
                    logger.info(f"{request_id} -- Output written to {file_path}")

            for record in progress:
                if record.status == ProgressStatus.NOTIFYING:
                    record.status = ProgressStatus.DONE

            self.db.session.commit()

            if not pending:
                self.send_mail(request_id)
                self.clean(request_id)

    def send_mail(self, request_id):
        if self.sender is not None:
            request = self.db.session.query(Request).filter_by(id=request_id).first()
            subject = 'Google map reviews'
            boby = '<h1>See more in attachment</h1>'
            attachment = f'./temp/{request_id}.csv'
            send_email_with_attachment(self.sender, request.email, subject, boby, attachment)

            logger.info(f"{request_id} -- Email sent: {request.email}")

    def clean(self, request_id):
        try:
            attachment_path = f'./temp/{request_id}.csv'
            if os.path.exists(attachment_path):
                os.remove(attachment_path)
                logger.info(f"{request_id} -- Deleted file")

            request = Request.query.get_or_404(request_id)
            self.db.session.delete(request)
            self.db.session.commit()

            logger.info(f"{request_id} -- Request clear")
        except Exception as e:
            self.db.session.rollback()
            logger.debug(f'{request_id} -- Request clear Error: {str(e)}')
