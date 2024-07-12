import aiohttp
import re
import logging
from bs4 import BeautifulSoup

from . import IScraper
from src.utils import singleton


logger = logging.getLogger(__name__)


@singleton
class HTMLScraper(IScraper):
    async def scrape(self, url):
        result = {'url': url, 'location': 'Deleted', 'reviewer': 'Deleted', 'content': 'Deleted'}

        async with (aiohttp.ClientSession() as session):
            redirect_url = ''
            async with session.get(url, allow_redirects=False) as response:
                location = str(response).split("Location': \'")[1].split("\'")[0]
                redirect_url = location.replace('hl=vi', 'hl=en')

            if not redirect_url:
                return {'url': url, 'location': 'Error', 'reviewer': 'Error', 'content': 'Error'}

            async with session.get(redirect_url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')

                    reviews_title_meta = soup.find('meta', {'itemprop': 'name'})
                    review_content_meta = soup.find('meta', {'itemprop': 'description'})

                    if reviews_title_meta:
                        reviews_title = reviews_title_meta.get('content')
                        reviews_title = reviews_title.replace('Google review of ', '')
                        reviews_title = reviews_title.split(' by ')

                        if len(reviews_title) > 1:
                            result['location'] = ' '.join(reviews_title[:-1])
                            result['reviewer'] = reviews_title[-1]
                        else:
                            result['location'] = ' '.join(reviews_title)

                    if review_content_meta:
                        review_content = review_content_meta.get('content')

                        pattern = r'★{0,5} \"?(.+)\"$'
                        clean_review_content = re.sub(pattern, r'\1', review_content)
                        result['content'] = clean_review_content
                        return result

        return result
