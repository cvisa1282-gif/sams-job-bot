import time
import re
from database import add_log
import os

ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))
ANTI_FLOOD_SECONDES = 3

_last_action = {}

MOTS_SUSPECTS = [
    "bot", "robot", "auto", "spam", "fake", "test", "admin",
    "hack", "cheat", "scam", "000", "111", "999"
]

def check_flood(user_id: int) -> bool:
    now = time.time()
    last = _last_action.get(user_id, 0)
    if now - last < ANTI_FLOOD_SECONDES:
        return False
    _last_action[user_id] = now
    return True

def is_nom_suspect(nom: str, username: str) -> bool:
    texte = (nom + username).lower()
    for mot in MOTS_SUSPECTS:
        if mot in texte:
            return True
    if re.search(r'\d{5,}', username):
        return True
    return False

def log_action(user_id: int, action: str, details: str = "", suspect: bool = False):
    try:
        add_log(user_id, action, details, suspect)
    except Exception as e:
        print(f"[LOG ERROR] {e}")

def is_valid_phone(numero: str) -> bool:
    cleaned = numero.replace("+", "").replace(" ", "").replace("-", "")
    return cleaned.isdigit() and 8 <= len(cleaned) <= 15

async def send_admin_alert(bot, message: str):
    try:
        await bot.send_message(ADMIN_ID, f"⚠️ *ALERTE SÉCURITÉ*\n\n{message}", parse_mode="Markdown")
    except Exception as e:
        print(f"[ADMIN ALERT ERROR] {e}")
