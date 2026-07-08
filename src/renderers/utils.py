import base64
import os


def logo_data_url() -> str:
    """Return the אל השד"ה logo as a base64 data URL for embedding in HTML."""
    base = os.path.join(os.path.dirname(__file__), '..', '..')
    candidates = [
        ('LOGO.png',  'image/png'),
        ('LOGO.jfif', 'image/jpeg'),
        ('LOGO.jpg',  'image/jpeg'),
    ]
    for fname, mime in candidates:
        path = os.path.normpath(os.path.join(base, fname))
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('ascii')
            return f"data:{mime};base64,{data}"
    return ""
