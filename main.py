import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

from src.pipeline import generate_roadmap, generate_all_rounds

# ─────────────────────────────────────────────
# הגדרת הקלט — ערוך כאן או ב-config.json
# ─────────────────────────────────────────────
CONFIG_FILE = "config.json"

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        my_input = json.load(f)
else:
    # ברירת מחדל אם אין config.json
    my_input = {
        "subject": "דמויות מופת",
        "topic":   "יחזקאל הנביא",
        "grade":   "ח׳",
        "rounds":  4,
    }

OUTPUT_DIR = "output"

# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n🚀 Al-Hashadeh Generator")
    print(f"   נושא: {my_input['subject']} | נושא: {my_input['topic']}")
    print(f"   כיתה: {my_input['grade']} | סבבים: {my_input['rounds']}")

    roadmap = generate_roadmap(my_input, OUTPUT_DIR)
    all_results = generate_all_rounds(my_input, roadmap, OUTPUT_DIR)

    print(f"\n📁 כל הקבצים שמורים ב: {os.path.abspath(OUTPUT_DIR)}/")
