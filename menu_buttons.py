from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import get_solde, get_ref_code, update_solde, add_retrait, update_retrait_statut, is_banni
from securite import check_flood, log_action
import os

ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "votre_bot")
MINIMUM_RETRAIT = 5000

RETRAIT_METHODE, RETRAIT_NUMERO, RETRAIT_PAYS, RETRAIT_MONTANT = range(4)

def get_menu_keyboard():
    keyboard = [
        ["💰 SOLDE", "🔗 PARRAINAGE"],
        ["💸 RETRAIT", "🚨 SIGNALER"],
        ["📩 CONTACT"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def btn_solde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    solde = get_solde(user_id)
    log_action(user_id, "CONSULTE_SOLDE")
    await update.message.reply_text(
        f"💰 *Votre solde actuel*\n\n"
        f"┌─────────────────────┐\n"
        f"│  💵 *{solde:.0f} FCFA*\n"
        f"└─────────────────────┘\n\n"
        f"📌 Retrait minimum : *5 000 FCFA*\n"
        f"💡 Parrainez des amis pour gagner plus !",
        parse_mode="Markdown"
    )

async def btn_parrainage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    ref_code = get_ref_code(user_id)
    from database import count_filleuls
    nb_filleuls = count_filleuls(user_id)
    lien = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
    log_action(user_id, "VU_PARRAINAGE")
    await update.message.reply_text(
        f"🔗 *Votre lien de parrainage*\n\n"
        f"`{lien}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Filleuls parrainés : *{nb_filleuls}*\n"
        f"💰 Par filleul : *+300 FCFA* pour vous\n"
        f"🎁 Bonus ami : *+150 FCFA* pour eux\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📲 Copiez ce lien et partagez-le !",
        parse_mode="Markdown"
    )

async def btn_retrait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    solde = get_solde(user_id)
    if solde < MINIMUM_RETRAIT:
        manque = MINIMUM_RETRAIT - solde
        await update.message.reply_text(
            f"❌ *Solde insuffisant*\n\n"
            f"💰 Votre solde : *{solde:.0f} FCFA*\n"
            f"📌 Minimum requis : *{MINIMUM_RETRAIT} FCFA*\n"
            f"📉 Il vous manque : *{manque:.0f} FCFA*\n\n"
            f"💡 Continuez à parrainer pour atteindre le seuil !",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton("📱 Moov Money", callback_data="methode_moov")],
        [InlineKeyboardButton("💳 Miss by YAS", callback_data="methode_yas")],
        [InlineKeyboardButton("❌ Annuler", callback_data="retrait_annuler")]
    ]
    await update.message.reply_text(
        f"💸 *Demande de retrait*\n\n"
        f"💰 Solde disponible : *{solde:.0f} FCFA*\n\n"
        f"Choisissez votre méthode de retrait :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return RETRAIT_METHODE

async def btn_retrait_methode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    methode = "Moov Money" if query.data == "methode_moov" else "Miss by YAS"
    context.user_data["retrait_methode"] = methode
    await query.edit_message_text(
        f"✅ Méthode : *{methode}*\n\n"
        f"📞 Entrez votre numéro de téléphone :",
        parse_mode="Markdown"
    )
    return RETRAIT_NUMERO

async def btn_retrait_numero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    numero = update.message.text.strip()
    if not numero.replace("+", "").replace(" ", "").isdigit() or len(numero) < 8:
        await update.message.reply_text("❌ Numéro invalide. Entrez un numéro correct (ex: +22500000000) :")
        return RETRAIT_NUMERO
    context.user_data["retrait_numero"] = numero
    await update.message.reply_text("🌍 Entrez votre pays (ex: Côte d'Ivoire) :")
    return RETRAIT_PAYS

async def btn_retrait_pays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pays = update.message.text.strip()
    if len(pays) < 2:
        await update.message.reply_text("❌ Pays invalide. Réessayez :")
        return RETRAIT_PAYS
    context.user_data["retrait_pays"] = pays
    solde = get_solde(update.effective_user.id)
    await update.message.reply_text(
        f"💰 Entrez le montant à retirer :\n"
        f"_(minimum {MINIMUM_RETRAIT} FCFA, votre solde : {solde:.0f} FCFA)_",
        parse_mode="Markdown"
    )
    return RETRAIT_MONTANT

async def btn_retrait_montant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        montant = float(update.message.text.strip().replace(" ", "").replace("fcfa", "").replace("FCFA", ""))
    except ValueError:
        await update.message.reply_text("❌ Montant invalide. Entrez un nombre (ex: 5000) :")
        return RETRAIT_MONTANT
    solde = get_solde(user_id)
    if montant < MINIMUM_RETRAIT:
        await update.message.reply_text(f"❌ Minimum : {MINIMUM_RETRAIT} FCFA. Réessayez :")
        return RETRAIT_MONTANT
    if montant > solde:
        await update.message.reply_text(f"❌ Solde insuffisant ({solde:.0f} FCFA). Réessayez :")
        return RETRAIT_MONTANT
    methode = context.user_data["retrait_methode"]
    numero = context.user_data["retrait_numero"]
    pays = context.user_data["retrait_pays"]
    update_solde(user_id, -montant)
    retrait_id = add_retrait(user_id, methode, numero, pays, montant)
    log_action(user_id, "DEMANDE_RETRAIT", f"{montant} FCFA via {methode}")
    keyboard_admin = [
        [InlineKeyboardButton("✅ Valider", callback_data=f"valider_{retrait_id}_{user_id}_{montant}"),
         InlineKeyboardButton("❌ Refuser", callback_data=f"refuser_{retrait_id}_{user_id}_{montant}")]
    ]
    user = update.effective_user
    await context.bot.send_message(
        ADMIN_ID,
        f"💸 *NOUVELLE DEMANDE DE RETRAIT*\n\n"
        f"👤 Utilisateur : {user.full_name} (`{user_id}`)\n"
        f"📱 Méthode : {methode}\n"
        f"📞 Numéro : {numero}\n"
        f"🌍 Pays : {pays}\n"
        f"💰 Montant : *{montant:.0f} FCFA*\n"
        f"🆔 Retrait ID : #{retrait_id}",
        reply_markup=InlineKeyboardMarkup(keyboard_admin),
        parse_mode="Markdown"
    )
    await update.message.reply_text(
        f"✅ *Demande envoyée !*\n\n"
        f"💰 Montant : *{montant:.0f} FCFA*\n"
        f"📱 Méthode : {methode}\n"
        f"📞 Numéro : {numero}\n\n"
        f"⏳ L'administrateur traitera votre demande sous 24h.\n"
        f"🔔 Vous serez notifié du résultat.",
        reply_markup=get_menu_keyboard(),
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def btn_retrait_annuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("❌ Retrait annulé.")
    await query.edit_message_text("❌ Demande de retrait annulée.")
    context.user_data.clear()
    return ConversationHandler.END

async def callback_valider_retrait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Accès refusé.", show_alert=True)
        return
    await query.answer()
    parts = query.data.split("_")
    retrait_id, user_id, montant = int(parts[1]), int(parts[2]), float(parts[3])
    update_retrait_statut(retrait_id, "valide")
    log_action(user_id, "RETRAIT_VALIDE", f"{montant} FCFA")
    await query.edit_message_text(f"✅ Retrait #{retrait_id} *VALIDÉ* — {montant:.0f} FCFA", parse_mode="Markdown")
    try:
        await context.bot.send_message(
            user_id,
            f"🎉 *Retrait approuvé !*\n\n"
            f"✅ Votre retrait de *{montant:.0f} FCFA* a été validé.\n"
            f"💳 Le paiement sera effectué très prochainement.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

async def callback_refuser_retrait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Accès refusé.", show_alert=True)
        return
    await query.answer()
    parts = query.data.split("_")
    retrait_id, user_id, montant = int(parts[1]), int(parts[2]), float(parts[3])
    update_solde(user_id, montant)
    update_retrait_statut(retrait_id, "refuse")
    log_action(user_id, "RETRAIT_REFUSE", f"{montant} FCFA remboursé")
    await query.edit_message_text(f"❌ Retrait #{retrait_id} *REFUSÉ* — {montant:.0f} FCFA remboursé", parse_mode="Markdown")
    try:
        await context.bot.send_message(
            user_id,
            f"❌ *Retrait refusé*\n\n"
            f"Votre retrait de *{montant:.0f} FCFA* a été refusé.\n"
            f"💰 Le montant a été *remboursé* sur votre solde.",
            parse_mode="Markdown"
        )
    except Exception:
        pass
