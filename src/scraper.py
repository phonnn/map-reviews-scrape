import aiohttp
from bs4 import BeautifulSoup


class Scraper:
    def extract_reviews(self, url):
        raise NotImplementedError("Subclasses must implement this method.")


class HTMLScraper(Scraper):
    async def extract_reviews(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')

                    reviewer_name_meta = soup.find('meta', {'itemprop': 'name'})
                    review_content_meta = soup.find('meta', {'itemprop': 'description'})

                    if reviewer_name_meta and review_content_meta:
                        reviewer_name = reviewer_name_meta.get('content')
                        review_content = review_content_meta.get('content')

                        clean_review_content = review_content.replace('★', '').strip()
                        return [url, reviewer_name, clean_review_content]

        return [url, 'Deleted', 'Deleted']
