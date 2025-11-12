import aiohttp
import base64
import binascii
import json
import logging
import re
import string
from typing import Callable, Dict, Iterable, Optional, Tuple

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

            state = self._load_app_state(html)
            if state is not None:
                state_data = await self._extract_from_app_state(state, session, redirect_url)
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
                location = response.headers.get('Location')
                if not location:
                    logger.debug("No Location header found when resolving review URL: %s", url)
                    return None
                return location.replace('hl=vi', 'hl=en')
        except aiohttp.ClientError as exc:
            logger.warning("Failed to resolve Google Maps review redirect: %s", exc)
            return None

    def _load_app_state(self, html: str) -> Optional[list]:
        sentinel = 'APP_INITIALIZATION_STATE='
        idx = html.find(sentinel)
        if idx == -1:
            return None

        start = html.find('[', idx)
        end = html.find('];', start)
        if start == -1 or end == -1:
            logger.debug("APP_INITIALIZATION_STATE markers malformed")
            return None

        raw = html[start : end + 1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.debug("Unable to decode APP_INITIALIZATION_STATE JSON: %s", exc)
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
                cleaned = re.sub(pattern, r'\1', description).strip()
                if cleaned and not all(ch == '★' for ch in cleaned):
                    extracted['content'] = cleaned
                else:
                    extracted['content'] = None

        return extracted

    async def _extract_from_app_state(
        self,
        state: list,
        session: aiohttp.ClientSession,
        referer: str,
    ) -> Dict[str, Optional[str]]:
        extracted: Dict[str, Optional[str]] = {
            'location': None,
            'reviewer': None,
            'content': None,
        }

        try:
            share_meta = state[9]
            if isinstance(share_meta, list) and share_meta:
                title = share_meta[0]
                location, reviewer = self._parse_title_string(title)
                extracted['location'] = location or extracted['location']
                extracted['reviewer'] = reviewer or extracted['reviewer']
        except (IndexError, TypeError):
            logger.debug("APP_INITIALIZATION_STATE share metadata layout differs from expectations")

        try:
            payload = state[13][4]
            decoded = self._decode_bfkj_payload(payload)
            if decoded:
                extracted['content'] = decoded.strip()
        except (IndexError, TypeError):
            logger.debug("bfkj payload slot not found in APP_INITIALIZATION_STATE")

        tokens = self._parse_review_tokens(state)
        if tokens and (extracted.get('content') is None or extracted.get('reviewer') is None):
            rpc_values = await self._hydrate_review_via_rpc(session, referer, *tokens)
            for key, value in rpc_values.items():
                if value:
                    extracted[key] = value

        return {key: value for key, value in extracted.items() if value is not None}

    def _parse_review_tokens(self, state: list) -> Optional[Tuple[str, str, str]]:
        try:
            review_bundle = state[5][3][13][0][1]
        except (IndexError, TypeError):
            logger.debug("Review token bundle not found in APP_INITIALIZATION_STATE")
            return None

        if not isinstance(review_bundle, list) or len(review_bundle) < 3:
            return None

        place_token = review_bundle[0]
        if not isinstance(place_token, str) or not place_token:
            return None

        review_token_array = review_bundle[2]
        review_token = None
        if isinstance(review_token_array, list) and review_token_array:
            review_token = review_token_array[0]

        if not isinstance(review_token, str) or '|' not in review_token:
            return None

        proto_part, cluster_part, *_rest = review_token.split('|') + [None, None]
        if not proto_part or ':' not in proto_part:
            return None

        encoded_review = proto_part.split(':', 1)[1]
        review_id = self._extract_review_id(encoded_review)
        cluster_id = self._decode_cluster_id(cluster_part)

        if review_id and cluster_id:
            return place_token, review_id, cluster_id

        return None

    def _extract_review_id(self, encoded: Optional[str]) -> Optional[str]:
        if not encoded:
            return None
        padded = encoded + '=' * (-len(encoded) % 4)
        try:
            decoded = base64.b64decode(padded)
        except (ValueError, binascii.Error):
            return None

        text = decoded.decode('utf-8', errors='ignore')
        marker = 'rp_'
        if marker not in text:
            return None

        start = text.index(marker)
        end = len(text)
        for delimiter in ('\x00', '"', "'", '\\'):
            idx = text.find(delimiter, start)
            if idx != -1:
                end = min(end, idx)

        review_id = text[start:end].strip()
        return review_id or None

    def _decode_cluster_id(self, encoded: Optional[str]) -> Optional[str]:
        if not encoded:
            return None
        padded = encoded + '=' * (-len(encoded) % 4)
        try:
            raw = base64.b64decode(padded)
        except (ValueError, binascii.Error):
            return None

        if not raw:
            return None

        cluster_int = int.from_bytes(raw, byteorder='big', signed=False)
        return str(cluster_int)

    async def _hydrate_review_via_rpc(
        self,
        session: aiohttp.ClientSession,
        referer: str,
        place_token: str,
        review_id: str,
        cluster_id: str,
    ) -> Dict[str, Optional[str]]:
        pb = self._build_review_rpc_pb(place_token, review_id, cluster_id)
        if not pb:
            return {}

        params = {
            'authuser': '0',
            'hl': 'en',
            'gl': 'us',
            'pb': pb,
        }
        headers = {
            'Referer': referer,
            'X-Same-Domain': '1',
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
        }

        try:
            async with session.get(
                'https://www.google.com/maps/preview/review/listentitiesreviews',
                params=params,
                headers=headers,
            ) as response:
                if response.status != 200:
                    logger.debug("Review RPC fetch failed: %s", response.status)
                    return {}
                payload = await response.text()
        except aiohttp.ClientError as exc:
            logger.debug("Review RPC request errored: %s", exc)
            return {}

        return self._parse_review_rpc_response(payload)

    def _build_review_rpc_pb(self, place_token: str, review_id: str, cluster_id: str) -> Optional[str]:
        if not (place_token and review_id and cluster_id):
            return None

        return (
            f'!1m2!1u{cluster_id}!2s{place_token}'
            f'!2m2!1i0!2i10'
            f'!3m2!1s{review_id}!2i1'
        )

    def _parse_review_rpc_response(self, payload: str) -> Dict[str, Optional[str]]:
        if payload.startswith(")]}'"):
            payload = payload[4:]

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.debug("Unable to decode review RPC payload: %s", exc)
            return {}

        reviewer: Optional[str] = None
        content: Optional[str] = None

        try:
            reviewer = data[2][0]
        except (IndexError, TypeError):
            reviewer = None

        try:
            translations = data[7][2][15]
            if isinstance(translations, list):
                for entry in translations:
                    if isinstance(entry, list) and entry:
                        text_candidate = entry[0]
                        if isinstance(text_candidate, str) and text_candidate.strip():
                            content = text_candidate.strip()
                            break
        except (IndexError, TypeError):
            content = None

        return {k: v for k, v in {'reviewer': reviewer, 'content': content}.items() if v}

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

        stripped = text.strip()
        if len(stripped) < 20:
            return False

        words = stripped.split()
        if len(words) < 5:
            return False

        alpha_chars = sum(1 for c in stripped if c.isalpha())
        if alpha_chars / max(len(stripped), 1) < 0.6:
            return False

        vowels = sum(1 for c in stripped.lower() if c in 'aeiou')
        if vowels < alpha_chars * 0.2:
            return False

        if not any(char.isspace() for char in stripped[:50]):
            return False

        sample = stripped.lower()
        keywords = ['review', 'service', 'google', 'experience', 'staff', 'place', 'clean', 'friendly']
        if any(keyword in sample for keyword in keywords):
            return True

        if any(punct in stripped for punct in ('.', '!', '?')):
            return True

        return False
