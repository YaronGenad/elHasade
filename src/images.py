"""
Image service — fetches topic-relevant images from Pexels (free) or
Gemini Imagen (paid fallback, $0.02/image) and caches them on disk.

Cache key: sha256(topic|grade|station)[:16] → cache/images/{key}.jpg
"""
import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


class ImageService:
    CACHE_DIR = Path(__file__).parent.parent / "cache" / "images"

    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY") or os.getenv("PEXEL_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    def fetch(self, topic: str, grade: str, station: str) -> Optional[str]:
        """Return absolute path to a cached image file, or None if unavailable."""
        key = hashlib.sha256(f"{topic}|{grade}|{station}".encode()).hexdigest()[:16]
        cache_path = self.CACHE_DIR / f"{key}.jpg"
        if cache_path.exists():
            return str(cache_path)
        data = self._try_pexels(topic) or self._try_imagen(topic, grade, station)
        if data:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            return str(cache_path)
        return None

    def _try_pexels(self, topic: str) -> Optional[bytes]:
        if not self.pexels_key:
            return None
        try:
            query = urllib.parse.quote(topic)
            url = f"https://api.pexels.com/v1/search?query={query}&per_page=3&orientation=landscape"
            req = urllib.request.Request(url, headers={"Authorization": self.pexels_key})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            photos = data.get("photos", [])
            if not photos:
                return None
            photo_url = photos[0]["src"]["medium"]
            with urllib.request.urlopen(photo_url, timeout=10) as img_resp:
                return img_resp.read()
        except Exception:
            return None

    def _try_imagen(self, topic: str, grade: str, station: str) -> Optional[bytes]:
        if not self.gemini_key:
            return None
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"imagen-4.0-fast-generate-001:predict?key={self.gemini_key}"
            )
            prompt = (
                f"educational illustration for Israeli elementary school, "
                f"topic: {topic}, grade {grade}, {station} worksheet activity, "
                "child-friendly, colorful, simple clean design, watercolor style"
            )
            body = json.dumps({
                "instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1},
            }).encode()
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            img_b64 = result["predictions"][0]["bytesBase64Encoded"]
            return base64.b64decode(img_b64)
        except Exception:
            return None

    @staticmethod
    def to_data_url(path: str) -> str:
        """Convert a local image file to a base64 data URL for HTML embedding."""
        ext = Path(path).suffix.lstrip(".").lower()
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{data}"
