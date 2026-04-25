from telegram import Update
from telegram.ext import ContextTypes
from database import (
    get_stats, get_all_users, set_banni, get_blacklist,
    get_logs, clear_logs, update_solde, set_solde, get_user
)
from securite import log_action
from menu_buttons import get_menu_keyboard
import os

ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⛔ Accès refusé.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper

@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_stats()
    await update.message.reply_text(
        f"📊 *STATISTIQUES SAMS-JOB*\n\n"
        f"👥 Total inscrits : *{s['total']}*\n"
        f"✅ Actifs : *{s['actifs']}*\n"
        f"🚫 Bannis : *{s['bannis']}*\n"
        f"🔗 Parrainages : *{s['parrainages']}*\n"
        f"💸 Retraits en attente : *{s['retraits_attente']}*",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /broadcast votre message")
        return
    message = " ".join(context.args)
    users = get_all_users()
    ok, fail = 0, 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"📢 *Message de l'admin :*\n\n{message}", parse_mode="Markdown")
            ok += 1
        except Exception:
            fail += 1
    await update.message.reply_text(f"✅ Envoyé à {ok} utilisateurs. ❌ Échoué : {fail}")

@admin_only
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /ban USER_ID raison")
        return
    try:
        user_id = int(context.args[0])
        raison = " ".join(context.args[1:]) or "Non précisée"
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    set_banni(user_id, True, raison)
    log_action(user_id, "BAN", f"Par admin. Raison: {raison}")
    await update.message.reply_text(f"🚫 Utilisateur `{user_id}` banni.\nRaison : {raison}", parse_mode="Markdown")
    try:
        await context.bot.send_message(user_id, "🚫 Votre compte a été suspendu par l'administrateur.")
    except Exception:
        pass

@admin_only
async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /unban USER_ID")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    set_banni(user_id, False)
    await update.message.reply_text(f"✅ Utilisateur `{user_id}` débanni.", parse_mode="Markdown")
    try:
        await context.bot.send_message(user_id, "✅ Votre compte a été réactivé. Bienvenue !")
    except Exception:
        pass

@admin_only
async def cmd_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    liste = get_blacklist()
    if not liste:
        await update.message.reply_text("✅ Aucun utilisateur banni.")
        return
    txt = "🚫 *LISTE NOIRE*\n\n"
    for row in liste:
        txt += f"• `{row['user_id']}` — {row['raison']} ({row['date_ban']})\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = get_logs(limit=30)
    if not logs:
        await update.message.reply_text("📭 Aucun log.")
        return
    txt = "📋 *DERNIERS LOGS*\n\n"
    for log in logs[:20]:
        suspect = " ⚠️" if log["suspect"] else ""
        txt += f"`{log['date_action']}` | {log['user_id']} | {log['action']}{suspect}\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_suspects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = get_logs(limit=30, suspects_only=True)
    if not logs:
        await update.message.reply_text("✅ Aucune activité suspecte.")
        return
    txt = "⚠️ *ACTIVITÉS SUSPECTES*\n\n"
    for log in logs[:20]:
        txt += f"`{log['date_action']}` | `{log['user_id']}` | {log['action']}\n_{log['details']}_\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_clearlogs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_logs()
    await update.message.reply_text("✅ Logs effacés.")

@admin_only
async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage : /reply USER_ID votre message")
        return
    try:
        user_id = int(context.args[0])
        message = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    try:
        await context.bot.send_message(
            user_id,
            f"📩 *Réponse de l'administrateur :*\n\n{message}",
            parse_mode="Markdown"
        )
        await update.message.reply_text(f"✅ Message envoyé à `{user_id}`.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {e}")

@admin_only
async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage : /add USER_ID MONTANT")
        return
    try:
        user_id = int(context.args[0])
        montant = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Paramètres invalides.")
        return
    update_solde(user_id, montant)
    log_action(user_id, "ADD_SOLDE", f"+{montant} FCFA par admin")
    await update.message.reply_text(f"✅ +{montant:.0f} FCFA ajoutés à `{user_id}`.", parse_mode="Markdown")

@admin_only
async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage : /remove USER_ID MONTANT")
        return
    try:
        user_id = int(context.args[0])
        montant = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Paramètres invalides.")
        return
    update_solde(user_id, -montant)
    log_action(user_id, "REMOVE_SOLDE", f"-{montant} FCFA par admin")
    await update.message.reply_text(f"✅ -{montant:.0f} FCFA retirés de `{user_id}`.", parse_mode="Markdown")

@admin_only
async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /reset USER_ID")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    set_solde(user_id, 0)
    log_action(user_id, "RESET_SOLDE", "Remis à 0 par admin")
    await update.message.reply_text(f"✅ Solde de `{user_id}` remis à 0.", parse_mode="Markdown")
