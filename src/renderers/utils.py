import base64
import os


def logo_data_url() -> str:
    """Return the אל השד"ה logo as a base64 data URL for embedding in HTML."""
    logo_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'LOGO.jfif'))
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        return f"data:image/jpeg;base64,{data}"
    return ""
