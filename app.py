import asyncio
import logging

from dotenv import load_dotenv
from flask import request, jsonify
load_dotenv()

from src.app_services.scrape import make_task
from src.datastore.models import db, Request, Progress, Review
from src import create_app
from src.scraper.scraper_service import HTMLScraper
from src.worker.queue import RedisQueue
from src.worker.worker import ScrapeWorker, Publisher
from src.writer.writer import CSVWriter
from flask_mail import Mail


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

redis = RedisQueue(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'])
scraper = HTMLScraper()
worker = ScrapeWorker(redis, scraper, db)

writer = CSVWriter()
mail_service = app.extensions["mail"]
publisher = Publisher(redis, db, writer, mail_service)


@app.route('/proxy', methods=['POST'])
def set_proxy():
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    proxy = data.get('proxy', None)
    scraper.register_proxy(proxy)

    return jsonify({"message": "Proxy settings updated successfully"}), 200

@app.route('/mail-server', methods=['POST'])
def change_mail_server():
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    app.config['MAIL_USERNAME'] = data.get('username', app.config['MAIL_USERNAME'])
    app.config['MAIL_PASSWORD'] = data.get('password', app.config['MAIL_PASSWORD'])

    # Re-initialize Flask-Mail with the updated settings
    mail_service = Mail(app)
    publisher.registerMailService(mail_service)

    return jsonify({"message": "Mail server settings updated successfully"}), 200


@app.route('/scrape', methods=['POST'])
def submit_request():
    data = request.json
    email = data['email']
    urls = data['urls']

    user_request = Request(email=email)
    db.session.add(user_request)
    db.session.commit()

    for url in urls:
        if make_task(url, user_request.id):
            asyncio.run(worker.start({'url': url}))

    return jsonify({'message': 'Request submitted successfully', 'request_id': user_request.id}), 200


async def main():
    pass
    logger.info('App starting...')
    worker_task = asyncio.create_task(worker.listen(app.app_context()))
    publisher_task = asyncio.create_task(publisher.listen(app.app_context()))

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, app.run, '0.0.0.0', 5000)

    await worker_task
    await publisher_task


if __name__ == '__main__':
    asyncio.run(main())
