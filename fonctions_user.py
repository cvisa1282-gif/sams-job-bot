from telegram import Update
from telegram.ext import ContextTypes
from database import is_banni, get_solde, get_ref_code, count_filleuls
from securite import check_flood, log_action
import sqlite3
import os

DB_PATH = "bot_data.db"

async def btn_classement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    top = conn.execute("""
        SELECT p.parrain_id, COUNT(*) as nb, u.full_name, u.username
        FROM parrainages p
        LEFT JOIN users u ON p.parrain_id = u.user_id
        GROUP BY p.parrain_id
        ORDER BY nb DESC LIMIT 10
    """).fetchall()
    mon_rang = conn.execute("""
        SELECT COUNT(*) + 1 as rang FROM (
            SELECT parrain_id, COUNT(*) as nb FROM parrainages
            GROUP BY parrain_id
            HAVING nb > (SELECT COUNT(*) FROM parrainages WHERE parrain_id = ?)
        )
    """, (user_id,)).fetchone()
    conn.close()
    medailles = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    txt = "🏆 *CLASSEMENT DES MEILLEURS PARRAINS*\n\n"
    if not top:
        txt += "Aucun parrainage encore.\nSoyez le premier ! 🚀"
    else:
        for i, row in enumerate(top):
            nom = (row["full_name"] or f"User {row['parrain_id']}")[:20]
            txt += f"{medailles[i]} *{nom}* — {row['nb']} filleul(s)\n"
    rang = mon_rang["rang"] if mon_rang else "?"
    mes_filleuls = count_filleuls(user_id)
    txt += f"\n━━━━━━━━━━━━━━━━━━━━\n📍 Votre position : *#{rang}*\n👥 Vos filleuls : *{mes_filleuls}*"
    log_action(user_id, "VU_CLASSEMENT")
    await update.message.reply_text(txt, parse_mode="Markdown")

async def btn_mon_rang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rang_f = conn.execute("""
        SELECT COUNT(*) + 1 as rang FROM (
            SELECT parrain_id, COUNT(*) as nb FROM parrainages
            GROUP BY parrain_id
            HAVING nb > (SELECT COUNT(*) FROM parrainages WHERE parrain_id = ?)
        )
    """, (user_id,)).fetchone()
    rang_s = conn.execute("""
        SELECT COUNT(*) + 1 as rang FROM users
        WHERE solde > (SELECT solde FROM users WHERE user_id = ?) AND est_banni = 0
    """, (user_id,)).fetchone()
    total = conn.execute("SELECT COUNT(*) as n FROM users WHERE est_banni=0").fetchone()["n"]
    conn.close()
    solde = get_solde(user_id)
    nb = count_filleuls(user_id)
    rf = rang_f["rang"] if rang_f else "?"
    rs = rang_s["rang"] if rang_s else "?"
    badge = "👑 Champion" if rf <= 3 else "🌟 Elite" if rf <= 10 else "🔥 Actif" if rf <= 50 else "🌱 Débutant"
    txt = (
        f"📍 *VOTRE RANG*\n\n🏅 Badge : *{badge}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Rang parrainage : *#{rf}* / {total}\n"
        f"💰 Rang solde : *#{rs}* / {total}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Filleuls : *{nb}*\n💵 Solde : *{solde:.0f} FCFA*"
    )
    log_action(user_id, "VU_RANG")
    await update.message.reply_text(txt, parse_mode="Markdown")

async def btn_mes_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    user_data = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    nb_filleuls = conn.execute("SELECT COUNT(*) as n FROM parrainages WHERE parrain_id = ?", (user_id,)).fetchone()["n"]
    retraits = conn.execute("SELECT COUNT(*) as nb, COALESCE(SUM(montant),0) as total FROM retraits WHERE user_id = ? AND statut = 'valide'", (user_id,)).fetchone()
    retraits_att = conn.execute("SELECT COUNT(*) as n FROM retraits WHERE user_id = ? AND statut='en_attente'", (user_id,)).fetchone()["n"]
    conn.close()
    solde = get_solde(user_id)
    total_gagne = nb_filleuls * 300
    date_join = user_data["date_join"][:10] if user_data and user_data["date_join"] else "?"
    ref_code = get_ref_code(user_id)
    txt = (
        f"📊 *VOS STATISTIQUES*\n\n"
        f"📅 Membre depuis : *{date_join}*\n"
        f"🔑 Code ref : `{ref_code}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *FINANCES*\n"
        f"💵 Solde : *{solde:.0f} FCFA*\n"
        f"📈 Total gagné : *{total_gagne:.0f} FCFA*\n"
        f"✅ Total retiré : *{retraits['total']:.0f} FCFA*\n"
        f"⏳ Retraits en attente : *{retraits_att}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 *PARRAINAGE*\n"
        f"👥 Total filleuls : *{nb_filleuls}*\n"
        f"💎 Gains parrainage : *{total_gagne:.0f} FCFA*\n\n"
        f"📉 Manque pour retrait : *{max(0, 5000-solde):.0f} FCFA*"
    )
    log_action(user_id, "VU_STATS")
    await update.message.reply_text(txt, parse_mode="Markdown")

# ─── FONCTION 34 : OBJECTIF ───────────────────────────────────────
async def btn_objectif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    objectif = conn.execute("SELECT valeur FROM parametres WHERE cle = ?", (f"objectif_{user_id}",)).fetchone()
    conn.close()
    solde = get_solde(user_id)
    if objectif:
        montant_obj = float(objectif["valeur"])
        progression = min(100, int((solde / montant_obj) * 100))
        barres = "🟩" * (progression // 10) + "⬜" * (10 - progression // 10)
        if solde >= montant_obj:
            txt = (
                f"🎯 *VOTRE OBJECTIF*\n\n"
                f"🎊 *FÉLICITATIONS !*\n"
                f"Vous avez atteint votre objectif de *{montant_obj:.0f} FCFA* !\n\n"
                f"💰 Solde actuel : *{solde:.0f} FCFA*\n\n"
                f"Fixez un nouvel objectif !\n"
                f"Tapez le montant souhaité :"
            )
            from database import set_parametre
            set_parametre(f"objectif_{user_id}", "0")
        else:
            manque = montant_obj - solde
            txt = (
                f"🎯 *VOTRE OBJECTIF*\n\n"
                f"💵 Objectif : *{montant_obj:.0f} FCFA*\n"
                f"💰 Solde actuel : *{solde:.0f} FCFA*\n"
                f"📉 Il manque : *{manque:.0f} FCFA*\n\n"
                f"📊 Progression :\n{barres} *{progression}%*\n\n"
                f"⚠️ *Atteignez votre objectif avant de retirer !*\n\n"
                f"Voulez-vous changer votre objectif ?\nTapez le nouveau montant ou /annuler :"
            )
    else:
        txt = (
            f"🎯 *FIXER UN OBJECTIF*\n\n"
            f"💰 Solde actuel : *{solde:.0f} FCFA*\n\n"
            f"Tapez le montant que vous souhaitez atteindre :\n"
            f"_(ex: 10000)_\n\n"
            f"⚠️ Tant que vous n'aurez pas atteint cet objectif,\n"
            f"vous ne pourrez pas effectuer de retrait !"
        )
    context.user_data["attente_objectif"] = True
    log_action(user_id, "VU_OBJECTIF")
    await update.message.reply_text(txt, parse_mode="Markdown")

async def btn_objectif_saisie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.user_data.get("attente_objectif"):
        return
    try:
        montant = float(update.message.text.strip().replace(" ", "").replace("fcfa", "").replace("FCFA", ""))
        if montant < 5000:
            await update.message.reply_text("❌ L'objectif minimum est 5 000 FCFA. Réessayez :")
            return
        from database import set_parametre
        set_parametre(f"objectif_{user_id}", str(montant))
        context.user_data.pop("attente_objectif", None)
        solde = get_solde(user_id)
        progression = min(100, int((solde / montant) * 100))
        barres = "🟩" * (progression // 10) + "⬜" * (10 - progression // 10)
        await update.message.reply_text(
            f"✅ *Objectif fixé !*\n\n"
            f"🎯 Objectif : *{montant:.0f} FCFA*\n"
            f"💰 Solde actuel : *{solde:.0f} FCFA*\n"
            f"📊 Progression : {barres} *{progression}%*\n\n"
            f"💪 Parrainez pour atteindre votre objectif !",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ Montant invalide. Entrez un nombre :")

# ─── FONCTION 43 : CONDITIONS ─────────────────────────────────────
async def btn_conditions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    txt = (
        f"📜 *CONDITIONS D'UTILISATION SAMS-JOB*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *CE QUI EST AUTORISÉ*\n"
        f"• Parrainer des amis réels\n"
        f"• Retirer ses gains légitimes\n"
        f"• Utiliser un seul compte\n"
        f"• Contacter le support en cas de problème\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ *CE QUI EST INTERDIT*\n"
        f"• Créer plusieurs comptes\n"
        f"• Utiliser des bots ou scripts\n"
        f"• Faux parrainages\n"
        f"• Numéros de retrait invalides\n"
        f"• Toute tentative de fraude\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚖️ *SANCTIONS*\n"
        f"• Bannissement définitif\n"
        f"• Solde annulé sans remboursement\n"
        f"• Signalement aux autorités si nécessaire\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 Dernière mise à jour : Avril 2026\n\n"
        f"En utilisant ce bot, vous acceptez ces conditions."
    )
    log_action(user_id, "VU_CONDITIONS")
    await update.message.reply_text(txt, parse_mode="Markdown")

# ─── FONCTION 46 : SUPPORT WHATSAPP ──────────────────────────────
async def btn_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banni(user_id):
        return
    if not check_flood(user_id):
        await update.message.reply_text("⏳ Attendez quelques secondes.")
        return
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [[
        InlineKeyboardButton(
            "💬 Contacter sur WhatsApp",
            url="https://wa.me/22899314796"
        )
    ]]
    txt = (
        f"📞 *SUPPORT PRIORITAIRE*\n\n"
        f"Vous avez un problème urgent ?\n"
        f"Contactez directement l'administrateur sur WhatsApp !\n\n"
        f"⏰ Disponible : *8h - 22h*\n"
        f"📱 Numéro : *+228 99 31 47 96*\n\n"
        f"Cliquez sur le bouton ci-dessous :"
    )
    log_action(user_id, "SUPPORT_WHATSAPP")
    await update.message.reply_text(
        txt,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
