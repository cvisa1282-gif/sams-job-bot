from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, create_user, update_solde, get_user_by_ref, add_parrainage, count_parrainages_heure, is_banni
from securite import check_flood, log_action, is_nom_suspect
from menu_buttons import get_menu_keyboard
import os

ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@votre_canal")
BONUS_PARRAIN = 300
BONUS_FILLEUL = 150
MAX_PARRAINAGES_PAR_HEURE = 5
BOT_USERNAME = os.environ.get("BOT_USERNAME", "votre_bot")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    if is_banni(user_id):
        await update.message.reply_text(
            "🚫 *Votre compte a été suspendu.*\n"
            "Contactez l'administrateur si vous pensez que c'est une erreur.",
            parse_mode="Markdown"
        )
        return

    if not check_flood(user_id):
        await update.message.reply_text("⏳ Trop vite ! Attendez quelques secondes.")
        return

    if is_nom_suspect(user.first_name or "", user.username or ""):
        log_action(user_id, "NOM_SUSPECT", f"Nom: {user.first_name} | @{user.username}", suspect=True)

    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["left", "kicked", "banned"]:
            keyboard = [
                [InlineKeyboardButton("📢 Rejoindre le canal", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
                [InlineKeyboardButton("✅ J'ai rejoint !", callback_data="check_join")]
            ]
            await update.message.reply_text(
                "📢 *Rejoignez notre canal officiel pour utiliser le bot !*\n\n"
                "Cliquez sur le bouton ci-dessous, puis revenez et cliquez sur ✅",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return
    except Exception:
        pass

    existing = get_user(user_id)
    if not existing:
        parrain_id = None
        ref_code_parrain = args[0] if args else None

        if ref_code_parrain:
            parrain = get_user_by_ref(ref_code_parrain)
            if parrain and parrain["user_id"] != user_id:
                parrain_id = parrain["user_id"]
                if count_parrainages_heure(parrain_id) >= MAX_PARRAINAGES_PAR_HEURE:
                    log_action(parrain_id, "LIMITE_PARRAINAGE",
                               f"Trop de filleuls en 1h. Filleul tenté: {user_id}", suspect=True)
                    parrain_id = None
                else:
                    update_solde(parrain_id, BONUS_PARRAIN)
                    add_parrainage(parrain_id, user_id)
                    log_action(parrain_id, "PARRAINAGE", f"Nouveau filleul: {user_id}")
                    try:
                        await context.bot.send_message(
                            parrain_id,
                            f"🎉 *Nouveau filleul !*\n\n"
                            f"Un ami vient de vous rejoindre.\n"
                            f"💰 +{BONUS_PARRAIN} FCFA ajoutés à votre solde !",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

        ref_code = create_user(user_id, user.username, user.full_name, parrain_id)

        if parrain_id:
            update_solde(user_id, BONUS_FILLEUL)
            bonus_txt = f"\n🎁 *Bonus de bienvenue :* +{BONUS_FILLEUL} FCFA"
        else:
            bonus_txt = ""

        log_action(user_id, "INSCRIPTION", f"Parrain: {parrain_id}")

        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"👤 *Nouvel inscrit*\n"
                f"ID: `{user_id}`\n"
                f"Nom: {user.full_name}\n"
                f"@{user.username or 'N/A'}\n"
                f"Parrain: {parrain_id or 'Aucun'}",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        message_accueil = (
            f"🎊 *Bienvenue sur SAMS-JOB, {user.first_name} !*\n\n"
            f"💼 Gagnez de l'argent facilement en parrainant vos amis !\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Comment ça marche ?*\n"
            f"• Partagez votre lien unique\n"
            f"• Chaque ami inscrit = +{BONUS_PARRAIN} FCFA pour vous\n"
            f"• Votre ami reçoit +{BONUS_FILLEUL} FCFA de bienvenue\n"
            f"• Retrait dès 5 000 FCFA\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{bonus_txt}\n\n"
            f"Choisissez une option ci-dessous 👇"
        )
    else:
        from database import get_solde
        solde = get_solde(user_id)
        message_accueil = (
            f"👋 *Bon retour, {user.first_name} !*\n\n"
            f"💰 Votre solde : *{solde:.0f} FCFA*\n\n"
            f"Que souhaitez-vous faire ? 👇"
        )

    await update.message.reply_text(
        message_accueil,
        reply_markup=get_menu_keyboard(),
        parse_mode="Markdown"
    )

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["left", "kicked", "banned"]:
            await query.answer("❌ Vous n'avez pas encore rejoint le canal !", show_alert=True)
        else:
            await query.message.delete()
            context.args = []
            await cmd_start(update, context)
    except Exception:
        await query.answer("✅ Vérification OK !", show_alert=True)
