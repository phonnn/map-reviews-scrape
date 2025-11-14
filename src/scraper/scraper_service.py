import asyncio
import random

import aiohttp
import re
import logging
from bs4 import BeautifulSoup

from . import IScraper
from src.utils import singleton

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/118.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Opera/79.0.4143.66 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Opera/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Version/120.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; Trident/7.0; AS; .NET CLR 4.0.30319; en-US) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; Trident/7.0; AS; .NET CLR 4.0.30319; en-US; .NET4.0E; .NET4.0C) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.70"
]


async def fetch_content(url, proxy=None):
    async with aiohttp.ClientSession() as session:
        try:
            user_agent = random.choice(USER_AGENTS)
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
                "Accept-Language": "en-US,en;",
                "Cache-Control": "max-age=0",
                "Priority": "u=0, i",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Service-Worker-Navigation-Preload": "true",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": user_agent
            }

            async with session.get(url, headers=headers, proxy=proxy) as response:
                content = await response.text()
                return content, None

        except Exception as e:
            logger.error(f'Error fetching URL {url}: {e}')
            return None, f'Error fetching URL {url}'



@singleton
class HTMLScraper(IScraper):
    def __init__(self, proxy=None):
        self.proxy = proxy

    def register_proxy(self, proxy):
        self.proxy = proxy

    async def scrape(self, url):
        result = {'url': url, 'location': 'Deleted', 'reviewer': 'Deleted', 'content': 'Deleted'}

        content, error = await fetch_content(url, self.proxy)

        if error:
            return {'url': url, 'location': 'Error', 'reviewer': 'Error', 'content': error}

        if content:
            soup = BeautifulSoup(content, 'html.parser')

            reviews_title_meta = soup.find('meta', {'itemprop': 'name'})
            review_content_meta = soup.find('meta', {'itemprop': 'description'})

            if reviews_title_meta:
                reviews_title = reviews_title_meta.get('content')

                if reviews_title.find('Google review of') != -1:
                    reviews_title = reviews_title.replace('Google review of ', '')
                    reviews_title = reviews_title.split(' by ')
                else:
                    reviews_title = reviews_title.replace('Bài đánh giá trên Google về ', '')
                    reviews_title = reviews_title.split(' của ')

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
