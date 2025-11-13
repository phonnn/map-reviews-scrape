import logging

from playwright.async_api import async_playwright

from . import IScraper
from src.utils import singleton


logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_NAVIGATION_TIMEOUT = 60_000
_CONTENT_WAIT_MS = 3_000


@singleton
class PlaywrightScraper(IScraper):
    async def scrape(self, url: str):
        result = {'url': url, 'location': 'Deleted', 'reviewer': 'Deleted', 'content': 'Deleted'}

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=_USER_AGENT, locale='en-US')
                page = await context.new_page()

                try:
                    await page.goto(url, wait_until="load", timeout=_NAVIGATION_TIMEOUT)
                    await page.wait_for_timeout(_CONTENT_WAIT_MS)

                    location_meta = await page.locator('meta[property="og:title"]').get_attribute('content')
                    if location_meta:
                        location_text = location_meta.replace('Google review of ', '').strip()
                        result['location'] = location_text

                    reviewer_locator = page.locator('button.fontTitleSmall').first
                    await reviewer_locator.wait_for(state='visible', timeout=_NAVIGATION_TIMEOUT)
                    result['reviewer'] = (await reviewer_locator.inner_text()).strip()

                    review_locator = page.locator('span.wiI7pd').first
                    await review_locator.wait_for(state='visible', timeout=_NAVIGATION_TIMEOUT)
                    result['content'] = (await review_locator.inner_text()).strip()

                    return result
                finally:
                    await context.close()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to scrape review for %s", url)
            return {'url': url, 'location': 'Error', 'reviewer': 'Error', 'content': 'Error'}
