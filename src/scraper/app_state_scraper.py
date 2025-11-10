import aiohttp
import base64
import binascii
import json
import logging
import re
import string
from typing import Callable, Dict, Iterable, Optional

from bs4 import BeautifulSoup

from . import IScraper
from src.utils import singleton


logger = logging.getLogger(__name__)


@singleton
class AppStateHTMLScraper(IScraper):
    """
    New scraper that prefers data embedded inside window.APP_INITIALIZATION_STATE.
    Falls back to the legacy meta-tag parsing when the app state is unavailable.
    """

    async def scrape(self, url: str) -> Dict[str, str]:
        result = {'url': url, 'location': 'Deleted', 'reviewer': 'Deleted', 'content': 'Deleted'}

        async with aiohttp.ClientSession() as session:
            redirect_url = await self._resolve_review_redirect(session, url)
            if not redirect_url:
                return {'url': url, 'location': 'Error', 'reviewer': 'Error', 'content': 'Error'}

            async with session.get(redirect_url) as response:
                if response.status != 200:
                    logger.debug("Google Maps review fetch failed: %s", response.status)
                    return result

                html = await response.text()

        # Primary path – parse APP_INITIALIZATION_STATE
        state_data = self._extract_from_app_state(html)
        for key, value in state_data.items():
            if value is not None:
                result[key] = value

        if result.get('content') not in (None, 'Deleted'):
            return result

        # Fallback path – legacy meta tags
        fallback = self._extract_from_meta_tags(html)
        for key, value in fallback.items():
            if value is not None:
                result[key] = value

        return result

    async def _resolve_review_redirect(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        try:
            async with session.get(url, allow_redirects=False) as response:
                # Prefer header instead of string parsing of the response repr
                location = response.headers.get('Location')
                if not location:
                    logger.debug("No Location header found when resolving review URL: %s", url)
                    return None
                return location.replace('hl=vi', 'hl=en')
        except aiohttp.ClientError as exc:
            logger.warning("Failed to resolve Google Maps review redirect: %s", exc)
            return None

    def _extract_from_meta_tags(self, html: str) -> Dict[str, Optional[str]]:
        soup = BeautifulSoup(html, 'html.parser')
        extracted: Dict[str, Optional[str]] = {'location': None, 'reviewer': None, 'content': None}

        title_meta = soup.find('meta', {'itemprop': 'name'})
        if title_meta:
            title = title_meta.get('content')
            if title:
                location, reviewer = self._parse_title_string(title)
                extracted['location'] = location
                extracted['reviewer'] = reviewer

        content_meta = soup.find('meta', {'itemprop': 'description'})
        if content_meta:
            description = content_meta.get('content')
            if description:
                pattern = r'★{0,5} \"?(.+)\"$'
                extracted['content'] = re.sub(pattern, r'\1', description)

        return extracted

    def _extract_from_app_state(self, html: str) -> Dict[str, Optional[str]]:
        sentinel = 'APP_INITIALIZATION_STATE='
        idx = html.find(sentinel)
        if idx == -1:
            return {}

        start = html.find('[', idx)
        end = html.find('];', start)
        if start == -1 or end == -1:
            logger.debug("APP_INITIALIZATION_STATE markers malformed")
            return {}

        raw = html[start : end + 1]
        try:
            state = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.debug("Unable to decode APP_INITIALIZATION_STATE JSON: %s", exc)
            return {}

        extracted: Dict[str, Optional[str]] = {
            'location': None,
            'reviewer': None,
            'content': None,
            'rating': None,
        }

        # Share card metadata contains the place/reviewer string and the star glyphs
        try:
            share_meta = state[9]
            if isinstance(share_meta, list) and share_meta:
                title = share_meta[0]
                description = share_meta[1] if len(share_meta) > 1 else ''
                location, reviewer = self._parse_title_string(title)
                extracted['location'] = location or extracted['location']
                extracted['reviewer'] = reviewer or extracted['reviewer']
                if isinstance(description, str):
                    star_count = description.count('★')
                    extracted['rating'] = str(star_count) if star_count else extracted['rating']
        except (IndexError, TypeError):
            logger.debug("APP_INITIALIZATION_STATE share metadata layout differs from expectations")

        # Attempt to decode the bfkj payload – review text may be stored here for some locales.
        try:
            payload = state[13][4]
            decoded = self._decode_bfkj_payload(payload)
            if decoded:
                extracted['content'] = decoded.strip()
        except (IndexError, TypeError):
            logger.debug("bfkj payload slot not found in APP_INITIALIZATION_STATE")

        return {key: value for key, value in extracted.items() if value is not None}

    def _parse_title_string(self, title: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not title:
            return None, None
        prefix = 'Google review of '
        if title.startswith(prefix):
            title = title[len(prefix) :]
        if ' by ' in title:
            location_part, reviewer = title.rsplit(' by ', 1)
            return location_part.strip() or None, reviewer.strip() or None
        return title.strip() or None, None

    def _decode_bfkj_payload(self, payload: Optional[str]) -> Optional[str]:
        if not payload or not isinstance(payload, str) or len(payload) < 4:
            return None

        base = payload[:-2]
        decoders = self._build_payload_decoders()

        for char in string.ascii_letters + string.digits + '+/':
            candidate = base + char + '=='
            try:
                data = base64.b64decode(candidate)
            except (ValueError, binascii.Error):
                continue

            text = self._bytes_to_text(data)
            if text and self._looks_like_natural_language(text):
                logger.debug("Decoded bfkj payload without compression using char %s", char)
                return text

            for decoder in decoders:
                try:
                    decoded_bytes = decoder(data)
                except Exception:
                    continue
                text = self._bytes_to_text(decoded_bytes)
                if text and self._looks_like_natural_language(text):
                    logger.debug("Decoded bfkj payload with %s using char %s", decoder.__name__, char)
                    return text

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

        return decoders

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
        sample = text.lower()
        keywords = ['review', 'service', 'google', 'experience', 'staff']
        score = sum(1 for keyword in keywords if keyword in sample)
        return score >= 2 or (len(sample.split()) > 6 and any(c.isalpha() for c in sample))
