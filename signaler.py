from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import is_banni
from securite import check_flood, log_action
from clavier import get_menu_keyboard
import os

ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))
SIGNALER_MESSAGE, CONTACT_MESSAGE = range(4, 6)

async def btn_signaler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return ConversationHandler.END
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return ConversationHandler.END
    await update.message.reply_text("🚨 *Signaler un problème*\n\nDécrivez votre problème :\n_(Tapez /annuler pour abandonner)_", parse_mode="Markdown")
    return SIGNALER_MESSAGE

async def btn_signaler_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    message = update.message.text.strip()
    if len(message) < 5:
        await update.message.reply_text("❌ Message trop court. Décrivez mieux :")
        return SIGNALER_MESSAGE
    log_action(user_id, "SIGNALEMENT", message[:200])
    try:
        await context.bot.send_message(ADMIN_ID, f"🚨 *SIGNALEMENT*\n\n👤 {user.full_name} (`{user_id}`)\n@{user.username or 'N/A'}\n\n📝 _{message}_", parse_mode="Markdown")
    except Exception:
        pass
    await update.message.reply_text("✅ *Signalement envoyé !*\n\nL'administrateur examinera votre problème.", reply_markup=get_menu_keyboard(), parse_mode="Markdown")
    return ConversationHandler.END

async def btn_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return ConversationHandler.END
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return ConversationHandler.END
    await update.message.reply_text("📩 *Contacter l'administrateur*\n\nTapez votre message :\n_(Tapez /annuler pour abandonner)_", parse_mode="Markdown")
    return CONTACT_MESSAGE

async def btn_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    message = update.message.text.strip()
    if len(message) < 3:
        await update.message.reply_text("❌ Message trop court. Réessayez :")
        return CONTACT_MESSAGE
    log_action(user_id, "CONTACT_ADMIN", message[:200])
    try:
        await context.bot.send_message(ADMIN_ID, f"📩 *MESSAGE CONTACT*\n\n👤 {user.full_name} (`{user_id}`)\n@{user.username or 'N/A'}\n\n📝 _{message}_\n\n💬 Répondre : `/reply {user_id} votre_message`", parse_mode="Markdown")
    except Exception:
        pass
    await update.message.reply_text("✅ *Message envoyé !*\n\nL'administrateur vous répondra bientôt.", reply_markup=get_menu_keyboard(), parse_mode="Markdown")
    return ConversationHandler.END

async def cmd_annuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Action annulée.", reply_markup=get_menu_keyboard())
    return ConversationHandler.END
