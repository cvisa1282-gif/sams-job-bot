from telegram import ReplyKeyboardMarkup

def get_menu_keyboard():
    keyboard = [
        ["💰 SOLDE", "🔗 PARRAINAGE"],
        ["💸 RETRAIT", "🚨 SIGNALER"],
        ["📊 MES STATS", "🎯 OBJECTIF"],
        ["📜 CONDITIONS", "📞 SUPPORT"],
        ["📩 CONTACT"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
