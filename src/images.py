"""
Image service — fetches topic-relevant images and caches them on disk.

Fetch priority:
  1. Disk cache  (sha256(topic|grade|station)[:16] → cache/images/{key}.jpg)
  2. Pexels API  (free tier, requires PEXELS_API_KEY env var)
  3. Wikimedia Commons  (completely free, no API key needed)
  4. Imagen 4.0  (paid, requires Google AI paid plan)
"""
import base64
import hashlib
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger(__name__)

# Module-level cache: avoid repeating the same translation across rounds/stations
_translation_cache: dict = {}


class ImageService:
    CACHE_DIR = Path(__file__).parent.parent / "cache" / "images"

    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY") or os.getenv("PEXEL_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    def fetch(self, topic: str, grade: str, station: str, round_num: int = 1) -> Optional[str]:
        """Return absolute path to a cached image file, or None if unavailable."""
        key = hashlib.sha256(f"{topic}|{grade}|{station}|{round_num}".encode()).hexdigest()[:16]
        cache_path = self.CACHE_DIR / f"{key}.jpg"
        if cache_path.exists():
            return str(cache_path)

        english_topic = self._translate_topic_for_pexels(topic)
        data = (
            self._try_pexels(english_topic, round_num)
            or self._try_wikimedia(topic)
            or self._try_imagen(topic, grade, station)
        )
        if data:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            log.info("image_cached", key=key, topic=topic, round=round_num, bytes=len(data))
            return str(cache_path)

        log.warning("image_fetch_failed", topic=topic, grade=grade, station=station, round=round_num)
        return None

    def _translate_topic_for_pexels(self, topic: str) -> str:
        """Translate Hebrew topic to English keywords for better Pexels results."""
        if all(ord(c) < 128 for c in topic.replace(' ', '')):
            return topic
        if topic in _translation_cache:
            return _translation_cache[topic]
        try:
            key = self.gemini_key or os.getenv("GEMINI_API_KEY_2")
            if not key:
                return topic
            from google import genai as _genai
            client = _genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=(
                    f"Translate this Hebrew topic to 2-3 English search keywords for image search: {topic}\n"
                    f"Return ONLY the English keywords, nothing else, no punctuation."
                ),
            )
            translated = response.text.strip()
            if translated and len(translated) < 80:
                log.info("topic_translated_for_pexels", original=topic, translated=translated)
                _translation_cache[topic] = translated
                return translated
        except Exception as exc:
            log.warning("topic_translation_failed", topic=topic, error=str(exc))
        _translation_cache[topic] = topic
        return topic

    # ── Pexels ──────────────────────────────────────────────────────────────────

    def _try_pexels(self, topic: str, round_num: int = 1) -> Optional[bytes]:
        if not self.pexels_key:
            return None
        try:
            query = urllib.parse.quote(topic)
            url = f"https://api.pexels.com/v1/search?query={query}&per_page=10&orientation=landscape"
            req = urllib.request.Request(url, headers={"Authorization": self.pexels_key})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            photos = data.get("photos", [])
            if not photos:
                return None
            # Pick a different photo for each round using modulo so we cycle through results
            photo_index = (round_num - 1) % len(photos)
            photo_url = photos[photo_index]["src"]["medium"]
            with urllib.request.urlopen(photo_url, timeout=10) as img_resp:
                return img_resp.read()
        except Exception as exc:
            log.warning("pexels_failed", topic=topic, error=str(exc))
            return None

    # ── Wikimedia Commons (free, no API key) ─────────────────────────────────────

    def _try_wikimedia(self, topic: str) -> Optional[bytes]:
        """Search Wikimedia Commons for a relevant image thumbnail (400px wide)."""
        # Try the topic directly, then first word only as a fallback
        search_queries = [topic]
        first_word = topic.split()[0] if topic.split() else topic
        if first_word != topic:
            search_queries.append(first_word)

        for query in search_queries:
            result = self._wikimedia_search_download(query)
            if result:
                return result
        return None

    def _wikimedia_search_download(self, query: str) -> Optional[bytes]:
        try:
            search_url = (
                "https://commons.wikimedia.org/w/api.php"
                f"?action=query&list=search"
                f"&srsearch={urllib.parse.quote(query)}"
                "&srnamespace=6&format=json&srlimit=8"
            )
            req = urllib.request.Request(
                search_url, headers={"User-Agent": "AlHasadeBot/1.0 (educational)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            results = data.get("query", {}).get("search", [])
            # Filter to raster image file types (exclude SVG)
            image_results = [
                r for r in results
                if any(r["title"].lower().endswith(ext) for ext in
                       (".jpg", ".jpeg", ".png", ".gif"))
            ]
            if not image_results:
                return None

            # Try first few candidates in case one fails to download
            for candidate in image_results[:3]:
                title = candidate["title"]
                info_url = (
                    "https://commons.wikimedia.org/w/api.php"
                    f"?action=query&titles={urllib.parse.quote(title)}"
                    "&prop=imageinfo&iiprop=url&iiurlwidth=400&format=json"
                )
                req2 = urllib.request.Request(
                    info_url, headers={"User-Agent": "AlHasadeBot/1.0 (educational)"}
                )
                with urllib.request.urlopen(req2, timeout=10) as resp2:
                    info = json.loads(resp2.read())

                pages = info.get("query", {}).get("pages", {})
                for _, page in pages.items():
                    for img_info in page.get("imageinfo", []):
                        thumb_url = img_info.get("thumburl") or img_info.get("url", "")
                        if not thumb_url:
                            continue
                        req3 = urllib.request.Request(
                            thumb_url, headers={"User-Agent": "AlHasadeBot/1.0 (educational)"}
                        )
                        with urllib.request.urlopen(req3, timeout=15) as img_resp:
                            return img_resp.read()

            return None

        except Exception as exc:
            log.warning("wikimedia_failed", query=query, error=str(exc))
            return None

    # ── Decorative bottom illustration ───────────────────────────────────────────

    def fetch_decorative(self, topic: str, station: str, round_num: int = 1) -> Optional[str]:
        """Fetch a decorative illustration for page bottom via Imagen (cached)."""
        key = hashlib.sha256(f"deco|{topic}|{station}|{round_num}".encode()).hexdigest()[:16]
        cache_path = self.CACHE_DIR / f"{key}.jpg"
        if cache_path.exists():
            return str(cache_path)

        english_topic = self._translate_topic_for_pexels(topic)
        prompt = (
            f"Decorative educational clipart illustration for a worksheet about '{english_topic}'. "
            f"Style: clean colorful clipart, child-friendly, white background, no text, "
            f"horizontal composition, themed illustrations relevant to the topic."
        )
        data = self._try_imagen_prompt(prompt)
        if data:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            log.info("decorative_image_cached", key=key, topic=topic, station=station)
            return str(cache_path)

        log.warning("decorative_image_failed", topic=topic, station=station)
        return None

    # ── Imagen 4 (paid plan required) ────────────────────────────────────────────

    def _try_imagen(self, topic: str, grade: str, station: str) -> Optional[bytes]:
        prompt = (
            f"educational illustration for Israeli elementary school, "
            f"topic: {topic}, grade {grade}, {station} worksheet activity, "
            "child-friendly, colorful, simple clean design, watercolor style"
        )
        return self._try_imagen_prompt(prompt)

    def _try_imagen_prompt(self, prompt: str) -> Optional[bytes]:
        """Call Imagen 4 with a custom prompt. Returns raw image bytes or None."""
        body = json.dumps({
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1},
        }).encode()

        keys = [k for k in [self.gemini_key, os.getenv("GEMINI_API_KEY_2")] if k]
        for key in keys:
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"imagen-4.0-generate-001:predict?key={key}"
                )
                req = urllib.request.Request(
                    url, data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=45) as resp:
                    result = json.loads(resp.read())
                img_b64 = result["predictions"][0]["bytesBase64Encoded"]
                return base64.b64decode(img_b64)
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode()[:300]
                log.warning("imagen_failed", key_prefix=key[:12], http_code=exc.code, error=err_body)
                continue
            except Exception as exc:
                log.warning("imagen_failed", key_prefix=key[:12] if key else "none", error=str(exc))
                continue
        return None

    @staticmethod
    def to_data_url(path: str) -> str:
        """Convert a local image file to a base64 data URL for HTML embedding."""
        ext = Path(path).suffix.lstrip(".").lower()
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{data}"
