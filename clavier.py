from telegram import ReplyKeyboardMarkup

def get_menu_keyboard():
    keyboard = [
        ["💰 SOLDE", "🔗 PARRAINAGE"],
        ["💸 RETRAIT", "🚨 SIGNALER"],
        ["🏆 CLASSEMENT", "📊 MES STATS"],
        ["📍 MON RANG", "📩 CONTACT"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
