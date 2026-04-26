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
