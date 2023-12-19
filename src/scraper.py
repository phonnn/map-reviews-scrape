import aiohttp
import re
from bs4 import BeautifulSoup


class Scraper:
    def extract_reviews(self, url):
        raise NotImplementedError("Subclasses must implement this method.")


class HTMLScraper(Scraper):
    async def extract_reviews(self, url):
        result = [url, 'Deleted', 'Deleted', 'Deleted']

        async with (aiohttp.ClientSession() as session):
            redirect_url = ''
            async with session.get(url, allow_redirects=False) as response:
                location = str(response).split("Location': \'")[1].split("\'")[0]
                redirect_url = location.replace('hl=vi', 'hl=en')

            if not redirect_url:
                return [url, 'Error', 'Error', 'Error']

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
                            result[1] = ' '.join(reviews_title[:-1])
                            result[2] = reviews_title[-1]
                        else:
                            result[1] = ' '.join(reviews_title)

                    if review_content_meta:
                        review_content = review_content_meta.get('content')

                        pattern = r'★{0,5} \"?(.+)\"$'
                        clean_review_content = re.sub(pattern, r'\1', review_content)
                        result[3] = clean_review_content
                        return result

        return result
