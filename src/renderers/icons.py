"""
Station SVG icons — white fill, viewBox 0 0 24 24 (Material Design paths).
Use inside a sized container; the SVG will fill 100%.
"""

ICON_COMPREHENSION = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="white">
  <path d="M21 5c-1.11-.35-2.33-.5-3.5-.5-1.95 0-4.05.4-5.5 1.5-1.45-1.1-3.55-1.5-5.5-1.5S2.45 4.9 1 6v14.65c0 .25.25.5.5.5.1 0 .15-.05.25-.05C3.1 20.45 5.05 20 6.5 20c1.95 0 3.75.4 5.25 1.25.6.35 1.2.75 1.75.75.55 0 1.15-.4 1.75-.75C16.75 20.4 18.55 20 20.5 20c1.45 0 3.4.45 4.75 1.1.1.05.15.05.25.05.25 0 .5-.25.5-.5V6c-.6-.45-1.25-.75-2-.95zm0 13.5c-1.1-.35-2.3-.5-3.5-.5-1.7 0-4.15.65-5.5 1.5V8c1.35-.85 3.8-1.5 5.5-1.5 1.2 0 2.4.15 3.5.5v11.5z"/>
</svg>"""

ICON_METHODS = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="white">
  <path d="M12 3L1 9l4 2.18V16s2.39 2 7 2 7-2 7-2v-4.82L23 9 12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99c-.91.52-2.56 1.01-5 1.01s-4.09-.49-5-1.01v-3.27l5 2.72 5-2.72v3.27z"/>
</svg>"""

ICON_PRECISION = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="white">
  <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
</svg>"""

ICON_VOCABULARY = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="white">
  <path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8zm-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12zm3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5s1.5.67 1.5 1.5S10.33 8 9.5 8zm5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8zm3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
</svg>"""

ICON_TEACHER = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="white">
  <path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
</svg>"""

ICON_ANSWERS = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="white">
  <path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
</svg>"""

STATION_ICONS: dict = {
    "comprehension": ICON_COMPREHENSION,
    "methods":       ICON_METHODS,
    "precision":     ICON_PRECISION,
    "vocabulary":    ICON_VOCABULARY,
    "teacher":       ICON_TEACHER,
    "answers":       ICON_ANSWERS,
}
