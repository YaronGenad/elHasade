"""
Image service — fetches topic-relevant images and caches them on disk.

Fetch priority (topic images):
  1. Disk cache  (sha256(topic|grade|station|round)[:16] → cache/images/{key}.jpg)
  2. Pexels API  (free tier, requires PEXELS_API_KEY env var) — topic-first queries
  3. Wikimedia Commons  (completely free, no API key needed)
  4. Imagen 4 Fast  (fast/cheap Google image gen, requires paid Gemini plan)
  5. Imagen 4  (high-quality Google image gen, paid plan)
  6. Gemini 2.5 Flash Image  ("Nano Banana" — cheapest custom image gen)

Decorative / SVG:
  - generate_svg_illustration(): topic-aware SVG banner via Gemini Flash text API
  - generate_mini_svgs(): list of small decorative SVGs for whitespace rows
  - fetch_decorative(): Imagen-based decorative illustration (cached)
"""
import base64
import hashlib
import json
import logging
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Optional

import structlog

log = structlog.get_logger(__name__)

# Module-level cache: avoid repeating the same translation across rounds/stations
_translation_cache: dict = {}
_translation_lock = threading.Lock()


def _identifier_for_bytes(data: bytes) -> str:
    """Stable per-image identifier used to detect duplicates within one generation."""
    return hashlib.sha256(data).hexdigest()[:16]


def _identifier_for_url(url: str) -> str:
    """Stable identifier for a remote photo URL (used before we download)."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _claim_unique(data: Optional[bytes], used_image_keys: Optional["UsedImageKeys"]) -> Optional[bytes]:
    """Return `data` if the tracker can claim its identifier; otherwise None."""
    if not data:
        return None
    if used_image_keys is None:
        return data
    if used_image_keys.try_claim(_identifier_for_bytes(data)):
        return data
    return None


class UsedImageKeys:
    """Thread-safe set of image identifiers already used in the current generation.

    Generation runs rounds in a ThreadPool, so multiple stations can hit the
    image service concurrently. `try_claim` atomically reserves an identifier:
    returns True if the caller now owns it, False if another caller already did.
    """

    def __init__(self):
        self._used: set[str] = set()
        self._lock = threading.Lock()

    def try_claim(self, identifier: str) -> bool:
        if not identifier:
            return True
        with self._lock:
            if identifier in self._used:
                return False
            self._used.add(identifier)
            return True

    def release(self, identifier: str) -> None:
        if not identifier:
            return
        with self._lock:
            self._used.discard(identifier)


class ImageService:
    CACHE_DIR = Path(__file__).parent.parent / "cache" / "images"

    # Topic comes FIRST so Pexels/Wikimedia searches are topic-driven
    STATION_PEXELS_QUERIES = {
        "comprehension": "{topic} reading story children",
        "methods":       "{topic} writing creative school",
        "precision":     "{topic} learning language letters",
        "vocabulary":    "{topic} symbols education colorful",
    }

    # Activity phrase used in SVG scene hints — kept short so topic dominates
    STATION_ACTIVITY_PHRASES = {
        "comprehension": "reading, discovering, learning",
        "methods":       "writing, creating, expressing",
        "precision":     "spelling, analyzing, language accuracy",
        "vocabulary":    "word cards, definitions, matching",
    }

    SVG_VARIATIONS = ["spring morning", "summer afternoon", "autumn evening", "winter day"]

    # Per-station offset into provider result lists, so different stations of the
    # same round pick different photos even when their queries overlap.
    STATION_OFFSETS = {
        "comprehension": 0,
        "methods":       5,
        "precision":     10,
        "vocabulary":    15,
    }

    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY") or os.getenv("PEXEL_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    # ── Public: topic image ──────────────────────────────────────────────────────

    def fetch(self, topic: str, grade: str, station: str, round_num: int = 1,
              hint: str = "", used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[str]:
        """Return absolute path to a cached image file, or None if unavailable.
        hint: story section_title + intro_sentence for context-aware image search.
        used_image_keys: optional per-generation tracker that prevents the same source
        image from being reused for a different station/round of the same generation."""
        hint_key = hashlib.sha256(hint[:60].encode()).hexdigest()[:8] if hint else ""
        key = hashlib.sha256(f"{topic}|{grade}|{station}|{round_num}|{hint_key}".encode()).hexdigest()[:16]
        cache_path = self.CACHE_DIR / f"{key}.jpg"
        if cache_path.exists():
            cached_id = _identifier_for_bytes(cache_path.read_bytes())
            if used_image_keys is None or used_image_keys.try_claim(cached_id):
                return str(cache_path)
            # Cache hit but the same bytes were already used in this generation —
            # fall through to fetch a different image and overwrite this cache slot.

        if hint:
            english_topic = self._translate_with_hint(topic, hint)
            pexels_query = english_topic
        else:
            english_topic = self._translate_topic_for_pexels(topic)
            query_template = self.STATION_PEXELS_QUERIES.get(station, "{topic} education")
            pexels_query = query_template.format(topic=english_topic)

        provider_calls = (
            lambda: self._try_pexels(pexels_query, round_num, station, used_image_keys),
            lambda: self._try_wikimedia(topic, round_num, station,
                                        english_hint=english_topic if hint else "",
                                        used_image_keys=used_image_keys),
            lambda: self._try_imagen_fast(topic, grade, station,
                                          hint=english_topic if hint else "",
                                          used_image_keys=used_image_keys),
            lambda: self._try_imagen(topic, grade, station,
                                     hint=english_topic if hint else "",
                                     used_image_keys=used_image_keys),
            lambda: self._try_gemini_image(english_topic, station, round_num,
                                           hint=english_topic if hint else "",
                                           used_image_keys=used_image_keys),
        )
        data = None
        for call in provider_calls:
            data = call()
            if data:
                break

        if data:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            log.info("image_cached", key=key, topic=topic, station=station, round=round_num, bytes=len(data))
            return str(cache_path)

        log.warning("image_fetch_failed", topic=topic, grade=grade, station=station, round=round_num)
        return None

    # ── Public: SVG illustrations ────────────────────────────────────────────────

    def generate_svg_illustration(self, topic: str, station: str, round_num: int = 1,
                                  used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[str]:
        """Generate a topic-aware colorful SVG banner. Returns path to cached .svg file."""
        key = hashlib.sha256(f"svg|{topic}|{station}|{round_num}".encode()).hexdigest()[:16]
        cache_path = self.CACHE_DIR / f"{key}.svg"
        if cache_path.exists():
            cached_id = _identifier_for_bytes(cache_path.read_bytes())
            if used_image_keys is None or used_image_keys.try_claim(cached_id):
                return str(cache_path)

        # Try a few variants if the first one collides with an already-used SVG
        svg_data = None
        for variant in range(len(self.SVG_VARIATIONS)):
            candidate = self._try_generate_svg(topic, station, round_num, variant=variant, mini=False)
            if not candidate:
                continue
            candidate_id = _identifier_for_bytes(candidate.encode("utf-8"))
            if used_image_keys is None or used_image_keys.try_claim(candidate_id):
                svg_data = candidate
                break
        if svg_data:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(svg_data, encoding="utf-8")
            log.info("svg_cached", key=key, topic=topic, station=station, round=round_num)
            return str(cache_path)

        log.warning("svg_generation_failed", topic=topic, station=station, round=round_num)
        return None

    def generate_mini_svgs(self, topic: str, station: str, round_num: int = 1,
                           count: int = 2,
                           used_image_keys: Optional["UsedImageKeys"] = None) -> List[str]:
        """Generate `count` small decorative SVGs (160×120) for whitespace rows.
        Returns list of cached .svg paths (may be shorter than count if generation fails)."""
        paths = []
        english_topic = self._translate_topic_for_pexels(topic)
        for variant in range(1, count + 1):
            key = hashlib.sha256(f"mini|{topic}|{station}|{round_num}|{variant}".encode()).hexdigest()[:16]
            cache_path = self.CACHE_DIR / f"{key}.svg"
            if cache_path.exists():
                cached_id = _identifier_for_bytes(cache_path.read_bytes())
                if used_image_keys is None or used_image_keys.try_claim(cached_id):
                    paths.append(str(cache_path))
                    continue
            svg_data = self._try_generate_svg(english_topic, station, round_num,
                                              variant=variant, mini=True)
            if svg_data:
                if used_image_keys is not None and \
                   not used_image_keys.try_claim(_identifier_for_bytes(svg_data.encode("utf-8"))):
                    continue
                self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(svg_data, encoding="utf-8")
                log.info("mini_svg_cached", key=key, topic=topic, station=station, variant=variant)
                paths.append(str(cache_path))
        return paths

    # ── Public: decorative bottom illustration ───────────────────────────────────

    def fetch_decorative(self, topic: str, station: str, round_num: int = 1,
                         used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[str]:
        """Fetch a decorative illustration for page bottom via Imagen (cached)."""
        key = hashlib.sha256(f"deco|{topic}|{station}|{round_num}".encode()).hexdigest()[:16]
        cache_path = self.CACHE_DIR / f"{key}.jpg"
        if cache_path.exists():
            cached_id = _identifier_for_bytes(cache_path.read_bytes())
            if used_image_keys is None or used_image_keys.try_claim(cached_id):
                return str(cache_path)

        english_topic = self._translate_topic_for_pexels(topic)
        prompt = (
            f"Decorative educational clipart illustration for a worksheet about '{english_topic}'. "
            f"Style: clean colorful clipart, child-friendly, white background, horizontal composition, "
            f"themed illustrations relevant to the topic. "
            "Do NOT include any text, letters, words, numbers, Hebrew characters, "
            "Arabic characters, or labels of any kind. Pure illustration only."
        )
        data = _claim_unique(self._try_imagen_fast_prompt(prompt), used_image_keys) \
            or _claim_unique(self._try_imagen_prompt(prompt), used_image_keys)
        if data:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            log.info("decorative_image_cached", key=key, topic=topic, station=station)
            return str(cache_path)

        log.warning("decorative_image_failed", topic=topic, station=station)
        return None

    # ── SVG generation internals ─────────────────────────────────────────────────

    def _build_svg_scene_hint(self, english_topic: str, station: str, variant: int = 0) -> str:
        """Build a topic-first scene description for SVG generation."""
        activity = self.STATION_ACTIVITY_PHRASES.get(station, "learning and discovering")
        mood = self.SVG_VARIATIONS[variant % len(self.SVG_VARIATIONS)]
        return f"{english_topic} theme: {activity} — {mood}, colorful children's educational illustration"

    def _try_generate_svg(self, topic: str, station: str, round_num: int,
                          variant: int = 0, mini: bool = False) -> Optional[str]:
        api_key = self.gemini_key or os.getenv("GEMINI_API_KEY_BECKUP")
        if not api_key:
            return None

        # If topic is Hebrew (not translated yet), translate first
        english_topic = self._translate_topic_for_pexels(topic)
        scene_hint = self._build_svg_scene_hint(english_topic, station, variant + round_num)

        if mini:
            viewbox = "0 0 160 120"
            size_desc = "small square (160×120)"
            element_count = "3-5"
        else:
            viewbox = "0 0 400 180"
            size_desc = "wide banner (400×180)"
            element_count = "4-7"

        prompt = (
            f"Create a simple colorful SVG illustration for an Israeli elementary school worksheet.\n"
            f"Scene: {scene_hint}.\n"
            f"Requirements:\n"
            f"- Pure SVG only, starting with <svg and ending with </svg>\n"
            f'- viewBox="{viewbox}" ({size_desc})\n'
            f"- Child-friendly, bright cheerful colors\n"
            f"- Simple geometric shapes and paths — no complex gradients\n"
            f"- ABSOLUTELY NO TEXT, LETTERS, NUMBERS, WORDS, or LABELS anywhere in the SVG\n"
            f"- Light or white background\n"
            f"- {element_count} visual elements clearly related to the topic/scene\n"
            f"Return ONLY the SVG markup, nothing else."
        )
        try:
            from google import genai as _genai
            client = _genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text.strip()
            if "```" in text:
                for block in text.split("```"):
                    stripped = block.strip()
                    for prefix in ("svg", "xml", ""):
                        stripped = stripped.removeprefix(prefix).strip()
                    if stripped.startswith("<svg"):
                        text = stripped
                        break
            if not text.startswith("<svg"):
                log.warning("svg_invalid_response", topic=topic, station=station, prefix=text[:60])
                return None
            return text
        except Exception as exc:
            log.warning("svg_generation_error", topic=topic, station=station, error=str(exc))
            return None

    @staticmethod
    def svg_inline(path: str) -> str:
        """Return SVG file content for direct inline HTML embedding."""
        return Path(path).read_text(encoding="utf-8")

    # ── Translation ───────────────────────────────────────────────────────────────

    def _translate_with_hint(self, topic: str, hint: str) -> str:
        """Translate topic + story title/intro to specific English visual keywords."""
        cache_key = f"{topic}|{hint[:40]}"
        # Read-only check — do NOT hold the lock during the API call
        with _translation_lock:
            if cache_key in _translation_cache:
                return _translation_cache[cache_key]
        try:
            key = (self.gemini_key or os.getenv("GEMINI_API_KEY_2")
                   or os.getenv("GEMINI_API_KEY_BECKUP"))
            if not key:
                return self._translate_topic_for_pexels(topic)
            from google import genai as _genai
            client = _genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=(
                    f"Translate this Hebrew educational story title to 4-6 specific English "
                    f"visual keywords suitable for searching historical illustrations, paintings, or photos.\n"
                    f"Topic: {topic}\n"
                    f"Story title/context: {hint}\n"
                    f"Rules:\n"
                    f"- Include the proper English name of the topic itself (e.g. Passover, Hanukkah, Purim, "
                    f"Independence Day) when the topic refers to a known holiday or event.\n"
                    f"- Add 2-4 culturally specific visual markers unique to THIS topic "
                    f"(e.g. matzah/seder plate for Passover, hamantaschen/masks for Purim, menorah/dreidel for Hanukkah, "
                    f"Israeli flag/blue and white for Independence Day) — never use generic Jewish or holiday imagery.\n"
                    f"- Avoid words that fit multiple holidays (family, meal, table, candles alone).\n"
                    f"Return ONLY English keywords separated by spaces, no punctuation, no explanations, max 6 words total."
                ),
            )
            translated = response.text.strip()
            if translated and len(translated) < 120:
                log.info("topic_translated_with_hint", original=hint[:60], translated=translated)
                with _translation_lock:
                    _translation_cache[cache_key] = translated
                return translated
        except Exception as exc:
            log.warning("topic_translation_with_hint_failed", topic=topic, error=str(exc))
        fallback = self._translate_topic_for_pexels(topic)
        with _translation_lock:
            _translation_cache[cache_key] = fallback
        return fallback

    def _translate_topic_for_pexels(self, topic: str) -> str:
        """Translate Hebrew topic to English keywords for better image search results."""
        if all(ord(c) < 128 for c in topic.replace(' ', '')):
            return topic
        # Read-only check — do NOT hold the lock during the API call
        with _translation_lock:
            if topic in _translation_cache:
                return _translation_cache[topic]
        try:
            key = self.gemini_key or os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY_BECKUP")
            if not key:
                with _translation_lock:
                    _translation_cache[topic] = topic
                return topic
            from google import genai as _genai
            client = _genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=(
                    f"Translate this Hebrew topic to specific English visual keywords for image search.\n"
                    f"Topic: {topic}\n"
                    f"Rules:\n"
                    f"- Include the proper English name of the topic itself (e.g. Passover, Hanukkah, Purim, "
                    f"Independence Day, Yom Kippur, April Fools) when the topic refers to a known holiday or event.\n"
                    f"- Add 2-3 culturally specific visual markers unique to THIS topic "
                    f"(matzah/seder plate for Passover, hamantaschen/masks for Purim, menorah/dreidel for Hanukkah, "
                    f"Israeli flag/blue and white for Independence Day, pranks/jokes for April Fools).\n"
                    f"- Avoid generic words that match multiple topics (family, meal, table, candles alone).\n"
                    f"Return ONLY English keywords separated by spaces, no punctuation, no explanations, max 5 words total."
                ),
            )
            translated = response.text.strip()
            if translated and len(translated) < 80:
                log.info("topic_translated_for_pexels", original=topic, translated=translated)
                with _translation_lock:
                    _translation_cache[topic] = translated
                return translated
        except Exception as exc:
            log.warning("topic_translation_failed", topic=topic, error=str(exc))
        with _translation_lock:
            _translation_cache[topic] = topic
        return topic

    # ── Pexels ───────────────────────────────────────────────────────────────────

    def _try_pexels(self, topic: str, round_num: int = 1, station: str = "",
                    used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[bytes]:
        if not self.pexels_key:
            return None
        try:
            query = urllib.parse.quote(topic)
            # Fetch enough results so 4 stations × 4 rounds = 16 distinct offsets fit
            url = f"https://api.pexels.com/v1/search?query={query}&per_page=40&orientation=landscape"
            req = urllib.request.Request(url, headers={
                "Authorization": self.pexels_key,
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            photos = data.get("photos", [])
            if not photos:
                return None
            station_offset = self.STATION_OFFSETS.get(station, 0)
            base_index = (station_offset + round_num - 1) % len(photos)
            for step in range(len(photos)):
                idx = (base_index + step) % len(photos)
                photo_url = photos[idx]["src"]["medium"]
                identifier = _identifier_for_url(photo_url)
                if used_image_keys is not None and not used_image_keys.try_claim(identifier):
                    continue
                try:
                    img_req = urllib.request.Request(
                        photo_url,
                        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"},
                    )
                    with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                        return img_resp.read()
                except Exception as inner_exc:
                    log.warning("pexels_download_failed", url=photo_url[:80], error=str(inner_exc))
                    if used_image_keys is not None:
                        used_image_keys.release(identifier)
                    continue
            return None
        except Exception as exc:
            log.warning("pexels_failed", topic=topic, error=str(exc))
            return None

    # ── Wikimedia Commons ────────────────────────────────────────────────────────

    def _try_wikimedia(self, topic: str, round_num: int = 1, station: str = "",
                       english_hint: str = "",
                       used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[bytes]:
        """Search Wikimedia Commons for a relevant image thumbnail (400px wide)."""
        search_queries = []
        if english_hint:
            search_queries.append(english_hint[:60])
        search_queries.append(topic)
        first_word = topic.split()[0] if topic.split() else topic
        if first_word != topic:
            search_queries.append(first_word)

        for query in search_queries:
            result = self._wikimedia_search_download(query, round_num, station, used_image_keys)
            if result:
                return result
        return None

    def _wikimedia_search_download(self, query: str, round_num: int = 1, station: str = "",
                                   used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[bytes]:
        try:
            search_url = (
                "https://commons.wikimedia.org/w/api.php"
                f"?action=query&list=search"
                f"&srsearch={urllib.parse.quote(query)}"
                "&srnamespace=6&format=json&srlimit=20"
            )
            req = urllib.request.Request(
                search_url, headers={"User-Agent": "AlHasadeBot/1.0 (educational)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            results = data.get("query", {}).get("search", [])
            image_results = [
                r for r in results
                if any(r["title"].lower().endswith(ext) for ext in
                       (".jpg", ".jpeg", ".png", ".gif"))
            ]
            if not image_results:
                return None

            station_offset = self.STATION_OFFSETS.get(station, 0)
            base_index = (station_offset + round_num - 1) % len(image_results)
            for step in range(len(image_results)):
                idx = (base_index + step) % len(image_results)
                candidate = image_results[idx]
                title = candidate["title"]
                identifier = _identifier_for_url(title)
                if used_image_keys is not None and not used_image_keys.try_claim(identifier):
                    continue
                info_url = (
                    "https://commons.wikimedia.org/w/api.php"
                    f"?action=query&titles={urllib.parse.quote(title)}"
                    "&prop=imageinfo&iiprop=url&iiurlwidth=400&format=json"
                )
                req2 = urllib.request.Request(
                    info_url, headers={"User-Agent": "AlHasadeBot/1.0 (educational)"}
                )
                try:
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
                except Exception as inner_exc:
                    log.warning("wikimedia_candidate_failed", title=title[:80], error=str(inner_exc))
                    if used_image_keys is not None:
                        used_image_keys.release(identifier)
                    continue

            return None

        except Exception as exc:
            log.warning("wikimedia_failed", query=query, error=str(exc))
            return None

    # ── Imagen 4 Fast ────────────────────────────────────────────────────────────

    def _try_imagen_fast(self, topic: str, grade: str, station: str, hint: str = "",
                         used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[bytes]:
        """Imagen 4 Fast — faster/cheaper variant for topic images."""
        if hint:
            prompt = (
                f"Illustration: {hint}. "
                "Style: child-friendly watercolor, white background, colorful. "
                "Do NOT include any text, letters, words, numbers, Hebrew characters, "
                "Arabic characters, or labels. Pure illustration only."
            )
        else:
            english_topic = self._translate_topic_for_pexels(topic)
            prompt = (
                f"educational illustration for Israeli elementary school, "
                f"topic: {english_topic}, grade {grade}, {station} worksheet activity, "
                "child-friendly, colorful, simple clean design, watercolor style. "
                "Do NOT include any text, letters, words, numbers, Hebrew characters, "
                "Arabic characters, or labels. Pure illustration only."
            )
        return _claim_unique(self._try_imagen_fast_prompt(prompt), used_image_keys)

    def _try_imagen_fast_prompt(self, prompt: str) -> Optional[bytes]:
        """Call Imagen 4 Fast with a custom prompt. Returns raw image bytes or None."""
        body = json.dumps({
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1},
        }).encode()

        keys = [k for k in [self.gemini_key,
                             os.getenv("GEMINI_API_KEY_2"),
                             os.getenv("GEMINI_API_KEY_BECKUP"),
                             os.getenv("GEMINI_API_KEY_BECKUP2")] if k]
        for key in keys:
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"imagen-4.0-fast-generate-001:predict?key={key}"
                )
                req = urllib.request.Request(
                    url, data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                img_b64 = result["predictions"][0]["bytesBase64Encoded"]
                return base64.b64decode(img_b64)
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode()[:300]
                log.warning("imagen_fast_failed", key_prefix=key[:12], http_code=exc.code, error=err_body)
                continue
            except Exception as exc:
                log.warning("imagen_fast_failed", key_prefix=key[:12] if key else "none", error=str(exc))
                continue
        return None

    # ── Imagen 4 ─────────────────────────────────────────────────────────────────

    def _try_imagen(self, topic: str, grade: str, station: str, hint: str = "",
                    used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[bytes]:
        if hint:
            prompt = (
                f"Illustration: {hint}. "
                "Style: child-friendly watercolor, white background, colorful. "
                "Do NOT include any text, letters, words, numbers, Hebrew characters, "
                "Arabic characters, or labels. Pure illustration only."
            )
        else:
            english_topic = self._translate_topic_for_pexels(topic)
            prompt = (
                f"educational illustration for Israeli elementary school, "
                f"topic: {english_topic}, grade {grade}, {station} worksheet activity, "
                "child-friendly, colorful, simple clean design, watercolor style. "
                "Do NOT include any text, letters, words, numbers, Hebrew characters, "
                "Arabic characters, or labels. Pure illustration only."
            )
        return _claim_unique(self._try_imagen_prompt(prompt), used_image_keys)

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

    # ── Gemini 2.5 Flash Image Generation ("Nano Banana") ────────────────────────

    def _try_gemini_image(self, english_topic: str, station: str, round_num: int,
                          hint: str = "",
                          used_image_keys: Optional["UsedImageKeys"] = None) -> Optional[bytes]:
        """Generate an image via Gemini 2.5 Flash Preview native image generation.
        Cheapest custom image generation option — final fallback before giving up."""
        if hint:
            prompt = (
                f"A colorful child-friendly educational illustration: {hint}. "
                "Style: bright watercolor, simple shapes, white background. "
                "Do NOT include any text, letters, words, numbers, Hebrew characters, "
                "Arabic characters, or labels of any kind. Pure illustration only."
            )
        else:
            activity = self.STATION_ACTIVITY_PHRASES.get(station, "learning")
            prompt = (
                f"A colorful child-friendly educational illustration about {english_topic}. "
                f"Theme: {activity}. Style: bright watercolor, simple shapes, white background. "
                "Do NOT include any text, letters, words, numbers, Hebrew characters, "
                "Arabic characters, or labels of any kind. Pure illustration only."
            )

        keys = [k for k in [
            self.gemini_key,
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_BECKUP"),
            os.getenv("GEMINI_API_KEY_BECKUP2"),
            os.getenv("GEMINI_API_KEY_3"),
            os.getenv("GEMINI_API_KEY_4"),
        ] if k]

        for key in keys:
            try:
                from google import genai as _genai
                from google.genai import types as _types
                client = _genai.Client(api_key=key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash-preview-native-image-generation",
                    contents=prompt,
                    config=_types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                        candidate_bytes = base64.b64decode(part.inline_data.data)
                        claimed = _claim_unique(candidate_bytes, used_image_keys)
                        if claimed is None:
                            # already used in this generation — try next key (new gen)
                            break
                        return claimed
                log.warning("gemini_image_no_image_part", topic=english_topic, station=station)
                return None
            except Exception as exc:
                log.warning("gemini_image_failed", key_prefix=key[:12] if key else "none",
                            topic=english_topic, error=str(exc))
                continue
        return None

    # ── Utilities ─────────────────────────────────────────────────────────────────

    @staticmethod
    def to_data_url(path: str) -> str:
        """Convert a local image file to a base64 data URL for HTML embedding."""
        ext = Path(path).suffix.lstrip(".").lower()
        if ext == "svg":
            mime = "image/svg+xml"
        elif ext in ("jpg", "jpeg"):
            mime = "image/jpeg"
        else:
            mime = f"image/{ext}"
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{data}"
