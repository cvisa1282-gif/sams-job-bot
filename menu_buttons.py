from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import (get_solde, get_ref_code, update_solde, add_retrait,
                      update_retrait_statut, is_banni, get_parametre,
                      is_numero_blackliste, is_pays_blackliste)
from securite import check_flood, log_action
from clavier import get_menu_keyboard
import os

ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "votre_bot")
MINIMUM_RETRAIT = 5000
RETRAIT_METHODE, RETRAIT_NUMERO, RETRAIT_PAYS, RETRAIT_MONTANT = range(4)

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
        f"💰 *Votre solde actuel*\n\n┌─────────────────────┐\n│  💵 *{solde:.0f} FCFA*\n└─────────────────────┘\n\n📌 Retrait minimum : *5 000 FCFA*\n💡 Parrainez des amis pour gagner plus !",
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
        f"🔗 *Votre lien de parrainage*\n\n`{lien}`\n\n━━━━━━━━━━━━━━━━━━━━\n👥 Filleuls : *{nb_filleuls}*\n💰 Par filleul : *+300 FCFA*\n🎁 Bonus ami : *+150 FCFA*\n━━━━━━━━━━━━━━━━━━━━\n\n📲 Copiez ce lien et partagez-le !",
        parse_mode="Markdown"
    )

async def btn_retrait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    retraits_bloques = get_parametre("retraits_bloques", "0")
    if retraits_bloques == "1":
        msg_blocage = get_parametre("message_blocage", "Les retraits sont temporairement suspendus.")
        await update.message.reply_text(f"🔒 *Retraits suspendus*\n\n{msg_blocage}", parse_mode="Markdown")
        return ConversationHandler.END
    min_retrait = int(get_parametre("minimum_retrait", str(MINIMUM_RETRAIT)))
    solde = get_solde(user_id)
    if solde < min_retrait:
        manque = min_retrait - solde
        await update.message.reply_text(
            f"❌ *Solde insuffisant*\n\n💰 Votre solde : *{solde:.0f} FCFA*\n📌 Minimum requis : *{min_retrait} FCFA*\n📉 Il vous manque : *{manque:.0f} FCFA*",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton("📱 Moov Money", callback_data="methode_moov")],
        [InlineKeyboardButton("💳 Miss by YAS", callback_data="methode_yas")],
        [InlineKeyboardButton("❌ Annuler", callback_data="retrait_annuler")]
    ]
    await update.message.reply_text(
        f"💸 *Demande de retrait*\n\n💰 Solde : *{solde:.0f} FCFA*\n\nChoisissez votre méthode :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return RETRAIT_METHODE

async def btn_retrait_methode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    methode = "Moov Money" if query.data == "methode_moov" else "Miss by YAS"
    context.user_data["retrait_methode"] = methode
    await query.edit_message_text(f"✅ Méthode : *{methode}*\n\n📞 Entrez votre numéro de téléphone :", parse_mode="Markdown")
    return RETRAIT_NUMERO

async def btn_retrait_numero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    numero = update.message.text.strip()
    if not numero.replace("+", "").replace(" ", "").isdigit() or len(numero) < 8:
        await update.message.reply_text("❌ Numéro invalide. Entrez un numéro correct :")
        return RETRAIT_NUMERO
    if is_numero_blackliste(numero):
        await update.message.reply_text("🚫 Ce numéro est bloqué. Contactez l'administrateur.")
        return ConversationHandler.END
    context.user_data["retrait_numero"] = numero
    await update.message.reply_text("🌍 Entrez votre pays (ex: Côte d'Ivoire) :")
    return RETRAIT_PAYS

async def btn_retrait_pays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pays = update.message.text.strip()
    if len(pays) < 2:
        await update.message.reply_text("❌ Pays invalide. Réessayez :")
        return RETRAIT_PAYS
    if is_pays_blackliste(pays):
        await update.message.reply_text("🚫 Les retraits ne sont pas disponibles dans votre pays.")
        return ConversationHandler.END
    context.user_data["retrait_pays"] = pays
    min_retrait = int(get_parametre("minimum_retrait", str(MINIMUM_RETRAIT)))
    solde = get_solde(update.effective_user.id)
    await update.message.reply_text(
        f"💰 Entrez le montant à retirer :\n_(minimum {min_retrait} FCFA, solde : {solde:.0f} FCFA)_",
        parse_mode="Markdown"
    )
    return RETRAIT_MONTANT

async def btn_retrait_montant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        montant = float(update.message.text.strip().replace(" ", "").replace("fcfa", "").replace("FCFA", ""))
    except ValueError:
        await update.message.reply_text("❌ Montant invalide. Entrez un nombre :")
        return RETRAIT_MONTANT
    min_retrait = int(get_parametre("minimum_retrait", str(MINIMUM_RETRAIT)))
    solde = get_solde(user_id)
    if montant < min_retrait:
        await update.message.reply_text(f"❌ Minimum : {min_retrait} FCFA. Réessayez :")
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
    keyboard_admin = [[
        InlineKeyboardButton("✅ Valider", callback_data=f"valider_{retrait_id}_{user_id}_{montant}"),
        InlineKeyboardButton("❌ Refuser", callback_data=f"refuser_{retrait_id}_{user_id}_{montant}")
    ]]
    user = update.effective_user
    await context.bot.send_message(
        ADMIN_ID,
        f"💸 *NOUVELLE DEMANDE DE RETRAIT*\n\n👤 {user.full_name} (`{user_id}`)\n📱 {methode}\n📞 {numero}\n🌍 {pays}\n💰 *{montant:.0f} FCFA*\n🆔 #{retrait_id}",
        reply_markup=InlineKeyboardMarkup(keyboard_admin),
        parse_mode="Markdown"
    )
    await update.message.reply_text(
        f"✅ *Demande envoyée !*\n\n💰 {montant:.0f} FCFA\n📱 {methode}\n📞 {numero}\n\n⏳ Traitement sous 24h.",
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
        await context.bot.send_message(user_id, f"🎉 *Retrait approuvé !*\n\n✅ *{montant:.0f} FCFA* validé.\n💳 Paiement en cours.", parse_mode="Markdown")
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
        await context.bot.send_message(user_id, f"❌ *Retrait refusé*\n\n*{montant:.0f} FCFA* remboursé sur votre solde.", parse_mode="Markdown")
    except Exception:
        pass
