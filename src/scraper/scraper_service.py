import aiohttp
import base64
import binascii
import json
import logging
import re
from typing import Callable, Iterable, Optional

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

                    app_state_data = self._parse_app_initialization_state(content)
                    if app_state_data:
                        result.update({k: v for k, v in app_state_data.items() if v is not None})
                        if result.get('content') not in (None, 'Deleted'):
                            return result

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

    def _parse_app_initialization_state(self, html: str) -> dict:
        """
        Attempt to extract review metadata from window.APP_INITIALIZATION_STATE.
        Google now places most of the interesting data inside this blob.
        """
        sentinel = 'APP_INITIALIZATION_STATE='
        start_idx = html.find(sentinel)
        if start_idx == -1:
            return {}

        start_idx = html.find('[', start_idx)
        end_idx = html.find('];', start_idx)
        if start_idx == -1 or end_idx == -1:
            return {}

        raw_json = html[start_idx:end_idx + 1]
        try:
            state = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.debug("Failed to json decode APP_INITIALIZATION_STATE: %s", exc)
            return {}

        extracted = {
            'location': None,
            'reviewer': None,
            'content': None,
            'rating': None,
        }

        # share card metadata – contains location name and star glyphs
        try:
            share_meta = state[9]
            if isinstance(share_meta, list) and share_meta:
                title = share_meta[0]
                description = share_meta[1] if len(share_meta) > 1 else ''
                location, reviewer = self._parse_title_string(title)
                extracted['location'] = location or extracted['location']
                extracted['reviewer'] = reviewer or extracted['reviewer']
                if isinstance(description, str) and description:
                    extracted['rating'] = description.count('★') or None
        except (IndexError, TypeError):
            logger.debug("APP_INITIALIZATION_STATE share metadata missing expected structure")

        # Attempt to decode the opaque bfkj payload that appears to hold richer data.
        try:
            payload = state[13][4]
            decoded = self._decode_bfkj_payload(payload)
            if decoded:
                extracted['content'] = decoded.strip()
        except (IndexError, TypeError):
            logger.debug("APP_INITIALIZATION_STATE bfkj payload missing expected structure")

        # Remove None entries to avoid overwriting defaults with nulls
        return {k: v for k, v in extracted.items() if v is not None}

    def _parse_title_string(self, title: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not title or not isinstance(title, str):
            return None, None
        prefix = 'Google review of '
        if title.startswith(prefix):
            title = title[len(prefix):]
        if ' by ' in title:
            location_part, reviewer = title.rsplit(' by ', 1)
            return location_part.strip() or None, reviewer.strip() or None
        return title.strip() or None, None

    def _decode_bfkj_payload(self, payload: Optional[str]) -> Optional[str]:
        if not payload or not isinstance(payload, str):
            return None

        # Google omits one Base64 character prior to the padding; brute force the missing symbol.
        base = payload[:-2]
        candidate_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

        decoders: Iterable[Callable[[bytes], Optional[bytes]]] = self._build_payload_decoders()

        for char in candidate_chars:
            candidate = base + char + '=='
            try:
                data = base64.b64decode(candidate)
            except (ValueError, binascii.Error):  # type: ignore[name-defined]
                continue

            # Try raw UTF-8 first
            text = self._bytes_to_text(data)
            if text and self._looks_like_natural_language(text):
                logger.debug("bfkj payload decoded without compression using char %s", char)
                return text

            for decoder in decoders:
                try:
                    decoded_bytes = decoder(data)
                except Exception:
                    continue
                text = self._bytes_to_text(decoded_bytes)
                if text and self._looks_like_natural_language(text):
                    logger.debug("bfkj payload decoded using %s and char %s", decoder.__name__, char)
                    return text

        logger.debug("Unable to decode bfkj payload – content remains unavailable")
        return None

    def _build_payload_decoders(self) -> Iterable[Callable[[bytes], Optional[bytes]]]:
        decoders: list[Callable[[bytes], Optional[bytes]]] = []

        try:
            import zlib

            def _zlib_decoder(data: bytes) -> Optional[bytes]:
                for wbits in (-15, 0, 8, 9, 10, 15):
                    try:
                        return zlib.decompress(data, wbits)
                    except zlib.error:
                        continue
                return None

            _zlib_decoder.__name__ = 'zlib'
            decoders.append(_zlib_decoder)
        except ModuleNotFoundError:
            pass

        try:
            import brotli

            def _brotli_decoder(data: bytes) -> Optional[bytes]:
                try:
                    return brotli.decompress(data)
                except brotli.error:
                    return None

            _brotli_decoder.__name__ = 'brotli'
            decoders.append(_brotli_decoder)
        except ModuleNotFoundError:
            pass

        try:
            import snappy

            def _snappy_decoder(data: bytes) -> Optional[bytes]:
                try:
                    return snappy.decompress(data)
                except Exception:
                    return None

            _snappy_decoder.__name__ = 'snappy'
            decoders.append(_snappy_decoder)
        except ModuleNotFoundError:
            pass

        try:
            from lz4 import frame as lz4frame

            def _lz4_decoder(data: bytes) -> Optional[bytes]:
                try:
                    return lz4frame.decompress(data)
                except Exception:
                    return None

            _lz4_decoder.__name__ = 'lz4'
            decoders.append(_lz4_decoder)
        except ModuleNotFoundError:
            pass

        return [decoder for decoder in decoders if decoder is not None]

    def _bytes_to_text(self, data: Optional[bytes]) -> Optional[str]:
        if not data:
            return None
        for encoding in ('utf-8', 'utf-16', 'utf-32', 'latin-1'):
            try:
                text = data.decode(encoding)
                if text:
                    return text
            except UnicodeDecodeError:
                continue
        return None

    def _looks_like_natural_language(self, text: str) -> bool:
        if not text:
            return False
        keywords = ['review', 'google', 'service', 'great', 'bad']
        score = sum(1 for kw in keywords if kw in text.lower())
        return score >= 2 or (len(text.split()) > 6 and any(c.isalpha() for c in text))
