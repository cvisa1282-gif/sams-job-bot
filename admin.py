from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_stats, get_all_users, set_banni, get_blacklist,
    get_logs, clear_logs, update_solde, set_solde, get_user,
    get_retraits_en_attente, update_retrait_statut,
    get_parametre, set_parametre,
    add_numero_blacklist, add_pays_blacklist,
    remove_pays_blacklist, get_pays_blacklist
)
from securite import log_action
import sqlite3, os
from datetime import datetime, timedelta

ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))
DB_PATH = "bot_data.db"

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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inscrits_today = conn.execute("SELECT COUNT(*) as n FROM users WHERE date_join >= date('now')").fetchone()["n"]
    conn.close()
    await update.message.reply_text(
        f"📊 *STATISTIQUES EN TEMPS RÉEL*\n\n"
        f"👥 Total inscrits : *{s['total']}*\n"
        f"🆕 Inscrits aujourd'hui : *{inscrits_today}*\n"
        f"✅ Actifs : *{s['actifs']}*\n"
        f"⚡ Actifs 7 jours : *{s['actifs_7j']}*\n"
        f"🚫 Bannis : *{s['bannis']}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Parrainages : *{s['parrainages']}*\n"
        f"💰 Gains distribués : *{s['total_gains']:.0f} FCFA*\n"
        f"💸 Retraits validés : *{s['total_retraits']:.0f} FCFA*\n"
        f"⏳ Retraits en attente : *{s['retraits_attente']}*",
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
    log_action(user_id, "BAN", f"Raison: {raison}")
    await update.message.reply_text(f"🚫 Utilisateur `{user_id}` banni.\nRaison : {raison}", parse_mode="Markdown")
    try:
        await context.bot.send_message(user_id, "🚫 Votre compte a été suspendu.")
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
        await context.bot.send_message(user_id, "✅ Votre compte a été réactivé !")
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
        await update.message.reply_text("Usage : /reply USER_ID message")
        return
    try:
        user_id = int(context.args[0])
        message = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    try:
        await context.bot.send_message(user_id, f"📩 *Réponse de l'administrateur :*\n\n{message}", parse_mode="Markdown")
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
    await update.message.reply_text(f"✅ Solde de `{user_id}` remis à 0.", parse_mode="Markdown")

@admin_only
async def cmd_retraits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    retraits = get_retraits_en_attente()
    if not retraits:
        await update.message.reply_text("✅ Aucun retrait en attente.")
        return
    txt = f"💸 *RETRAITS EN ATTENTE ({len(retraits)})*\n\n"
    for r in retraits[:10]:
        txt += f"🆔 #{r['id']} | {r['full_name']} (`{r['user_id']}`)\n💰 {r['montant']:.0f} FCFA | 📱 {r['methode']}\n📞 {r['numero']} | 🌍 {r['pays']}\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_valider_tout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /validertt ID1 ID2 ID3")
        return
    ok, fail = 0, 0
    for arg in context.args:
        try:
            retrait_id = int(arg)
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            r = conn.execute("SELECT * FROM retraits WHERE id = ?", (retrait_id,)).fetchone()
            conn.close()
            if r and r["statut"] == "en_attente":
                update_retrait_statut(retrait_id, "valide")
                try:
                    await context.bot.send_message(r["user_id"], f"🎉 *Retrait approuvé !*\n\n✅ *{r['montant']:.0f} FCFA* validé.", parse_mode="Markdown")
                except Exception:
                    pass
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1
    await update.message.reply_text(f"✅ {ok} retrait(s) validé(s). ❌ {fail} échoué(s).")

@admin_only
async def cmd_refuser_motif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage : /refuser ID motif")
        return
    try:
        retrait_id = int(context.args[0])
        motif = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM retraits WHERE id = ?", (retrait_id,)).fetchone()
    conn.close()
    if not r:
        await update.message.reply_text("❌ Retrait introuvable.")
        return
    update_solde(r["user_id"], r["montant"])
    update_retrait_statut(retrait_id, "refuse")
    await update.message.reply_text(f"❌ Retrait #{retrait_id} refusé. Motif : {motif}")
    try:
        await context.bot.send_message(r["user_id"], f"❌ *Retrait refusé*\n\n💰 *{r['montant']:.0f} FCFA* remboursé\n📝 Motif : _{motif}_", parse_mode="Markdown")
    except Exception:
        pass

@admin_only
async def cmd_paye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /paye RETRAIT_ID")
        return
    try:
        retrait_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    update_retrait_statut(retrait_id, "paye")
    await update.message.reply_text(f"✅ Retrait #{retrait_id} marqué comme *payé*.", parse_mode="Markdown")

@admin_only
async def cmd_bloquer_retraits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /bloquertt message pour les utilisateurs")
        return
    message = " ".join(context.args)
    set_parametre("retraits_bloques", "1")
    set_parametre("message_blocage", message)
    users = get_all_users()
    ok = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"🔒 *RETRAITS SUSPENDUS*\n\n{message}", parse_mode="Markdown")
            ok += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Retraits bloqués. Message envoyé à {ok} utilisateurs.")

@admin_only
async def cmd_debloquer_retraits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_parametre("retraits_bloques", "0")
    users = get_all_users()
    ok = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, "✅ *Les retraits sont à nouveau disponibles !*", parse_mode="Markdown")
            ok += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Retraits débloqués. Message envoyé à {ok} utilisateurs.")

@admin_only
async def cmd_set_minimum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /setmin MONTANT")
        return
    try:
        montant = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Montant invalide.")
        return
    set_parametre("minimum_retrait", str(montant))
    await update.message.reply_text(f"✅ Minimum fixé à *{montant} FCFA*.", parse_mode="Markdown")

@admin_only
async def cmd_retraits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    retraits = get_retraits_en_attente()
    if not retraits:
        await update.message.reply_text("✅ Aucun retrait en attente.")
        return
    txt = f"💸 *RETRAITS EN ATTENTE ({len(retraits)})*\n\n"
    for r in retraits[:10]:
        txt += f"🆔 #{r['id']} | {r['full_name']} (`{r['user_id']}`)\n💰 {r['montant']:.0f} FCFA | 📱 {r['methode']}\n📞 {r['numero']} | 🌍 {r['pays']}\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_valider_tout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /validertt ID1 ID2 ID3")
        return
    ok, fail = 0, 0
    for arg in context.args:
        try:
            retrait_id = int(arg)
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            r = conn.execute("SELECT * FROM retraits WHERE id = ?", (retrait_id,)).fetchone()
            conn.close()
            if r and r["statut"] == "en_attente":
                update_retrait_statut(retrait_id, "valide")
                try:
                    await context.bot.send_message(r["user_id"], f"🎉 *Retrait approuvé !*\n\n✅ *{r['montant']:.0f} FCFA* validé.", parse_mode="Markdown")
                except Exception:
                    pass
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1
    await update.message.reply_text(f"✅ {ok} retrait(s) validé(s). ❌ {fail} échoué(s).")

@admin_only
async def cmd_refuser_motif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage : /refuser ID motif")
        return
    try:
        retrait_id = int(context.args[0])
        motif = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM retraits WHERE id = ?", (retrait_id,)).fetchone()
    conn.close()
    if not r:
        await update.message.reply_text("❌ Retrait introuvable.")
        return
    update_solde(r["user_id"], r["montant"])
    update_retrait_statut(retrait_id, "refuse")
    await update.message.reply_text(f"❌ Retrait #{retrait_id} refusé. Motif : {motif}")
    try:
        await context.bot.send_message(r["user_id"], f"❌ *Retrait refusé*\n\n💰 *{r['montant']:.0f} FCFA* remboursé\n📝 Motif : _{motif}_", parse_mode="Markdown")
    except Exception:
        pass

@admin_only
async def cmd_paye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /paye RETRAIT_ID")
        return
    try:
        retrait_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    update_retrait_statut(retrait_id, "paye")
    await update.message.reply_text(f"✅ Retrait #{retrait_id} marqué comme *payé*.", parse_mode="Markdown")

@admin_only
async def cmd_bloquer_retraits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /bloquertt message pour les utilisateurs")
        return
    message = " ".join(context.args)
    set_parametre("retraits_bloques", "1")
    set_parametre("message_blocage", message)
    users = get_all_users()
    ok = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"🔒 *RETRAITS SUSPENDUS*\n\n{message}", parse_mode="Markdown")
            ok += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Retraits bloqués. Message envoyé à {ok} utilisateurs.")

@admin_only
async def cmd_debloquer_retraits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_parametre("retraits_bloques", "0")
    users = get_all_users()
    ok = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, "✅ *Les retraits sont à nouveau disponibles !*", parse_mode="Markdown")
            ok += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Retraits débloqués. Message envoyé à {ok} utilisateurs.")

@admin_only
async def cmd_set_minimum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /setmin MONTANT")
        return
    try:
        montant = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Montant invalide.")
        return
    set_parametre("minimum_retrait", str(montant))
    await update.message.reply_text(f"✅ Minimum fixé à *{montant} FCFA*.", parse_mode="Markdown")

@admin_only
async def cmd_fraudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = get_logs(limit=50, suspects_only=True)
    if not logs:
        await update.message.reply_text("✅ Aucune tentative de fraude.")
        return
    txt = "🚨 *TENTATIVES DE FRAUDE*\n\n"
    for log in logs[:15]:
        txt += f"`{log['date_action']}` | `{log['user_id']}`\n{log['action']} : _{log['details']}_\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_doublons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    doublons = conn.execute("SELECT username, COUNT(*) as nb FROM users WHERE username IS NOT NULL AND username != '' GROUP BY username HAVING nb > 1").fetchall()
    conn.close()
    if not doublons:
        await update.message.reply_text("✅ Aucun doublon détecté.")
        return
    txt = "⚠️ *COMPTES EN DOUBLON*\n\n"
    for d in doublons:
        txt += f"@{d['username']} → {d['nb']} comptes\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_ban_tel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /bantel NUMERO raison")
        return
    numero = context.args[0]
    raison = " ".join(context.args[1:]) or "Non précisée"
    add_numero_blacklist(numero, raison)
    await update.message.reply_text(f"✅ Numéro `{numero}` blacklisté.", parse_mode="Markdown")

@admin_only
async def cmd_ban_pays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /banpays PAYS raison")
        return
    pays = context.args[0]
    raison = " ".join(context.args[1:]) or "Non précisée"
    add_pays_blacklist(pays, raison)
    await update.message.reply_text(f"✅ Pays *{pays}* bloqué.", parse_mode="Markdown")

@admin_only
async def cmd_unban_pays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /unbanpays PAYS")
        return
    pays = context.args[0]
    remove_pays_blacklist(pays)
    await update.message.reply_text(f"✅ Pays *{pays}* débloqué.", parse_mode="Markdown")

@admin_only
async def cmd_liste_pays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pays = get_pays_blacklist()
    if not pays:
        await update.message.reply_text("✅ Aucun pays bloqué.")
        return
    txt = "🌍 *PAYS BLOQUÉS*\n\n"
    for p in pays:
        txt += f"• {p['pays']} — {p['raison']}\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_set_limite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage : /setlimite USER_ID MONTANT_MAX")
        return
    try:
        user_id = int(context.args[0])
        limite = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Paramètres invalides.")
        return
    set_parametre(f"limite_retrait_{user_id}", str(limite))
    await update.message.reply_text(f"✅ Limite de `{user_id}` fixée à *{limite:.0f} FCFA*.", parse_mode="Markdown")

@admin_only
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    suspects = get_logs(limit=100, suspects_only=True)
    doublons = conn.execute("SELECT COUNT(*) as n FROM (SELECT username FROM users WHERE username IS NOT NULL GROUP BY username HAVING COUNT(*) > 1)").fetchone()["n"]
    pays_bloques = conn.execute("SELECT COUNT(*) as n FROM blacklist_pays").fetchone()["n"]
    tel_bloques = conn.execute("SELECT COUNT(*) as n FROM blacklist_tel").fetchone()["n"]
    bannis = conn.execute("SELECT COUNT(*) as n FROM users WHERE est_banni=1").fetchone()["n"]
    conn.close()
    txt = (
        f"🔍 *AUDIT COMPLET DE SÉCURITÉ*\n\n"
        f"⚠️ Activités suspectes : *{len(suspects)}*\n"
        f"👥 Comptes en doublon : *{doublons}*\n"
        f"🚫 Utilisateurs bannis : *{bannis}*\n"
        f"📞 Numéros blacklistés : *{tel_bloques}*\n"
        f"🌍 Pays bloqués : *{pays_bloques}*\n\n"
        f"🛡 Statut : {'🔴 Attention requise' if len(suspects) > 10 else '🟢 Normal'}"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Usage : Envoyez une photo, répondez avec /broadcastphoto texte")
        return
    photo = update.message.reply_to_message.photo[-1].file_id
    caption = " ".join(context.args) if context.args else ""
    users = get_all_users()
    ok, fail = 0, 0
    for uid in users:
        try:
            await context.bot.send_photo(uid, photo, caption=caption, parse_mode="Markdown")
            ok += 1
        except Exception:
            fail += 1
    await update.message.reply_text(f"✅ Photo envoyée à {ok} utilisateurs. ❌ {fail}")

@admin_only
async def cmd_programme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage : /programme HH:MM message")
        return
    heure_str = context.args[0]
    message = " ".join(context.args[1:])
    try:
        heure = datetime.strptime(heure_str, "%H:%M")
        now = datetime.now()
        target = now.replace(hour=heure.hour, minute=heure.minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        delai = (target - now).total_seconds()
        set_parametre("msg_programme", message)
        await update.message.reply_text(f"⏰ Message programmé pour *{heure_str}*\n📝 _{message}_\n\nDans {int(delai//60)} minutes.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Format invalide. Utilisez HH:MM")

@admin_only
async def cmd_annonce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /annonce votre message")
        return
    message = " ".join(context.args)
    users = get_all_users()
    ok, fail = 0, 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"📣 *ANNONCE IMPORTANTE*\n\n{message}", parse_mode="Markdown")
            ok += 1
        except Exception:
            fail += 1
    await update.message.reply_text(f"📣 Annonce envoyée à {ok} utilisateurs.")

@admin_only
async def cmd_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /maintenance détails")
        return
    message = " ".join(context.args)
    users = get_all_users()
    ok = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"🔧 *MAINTENANCE PRÉVUE*\n\n{message}\n\n⏳ Merci de votre patience.", parse_mode="Markdown")
            ok += 1
        except Exception:
            pass
    await update.message.reply_text(f"🔧 Notification envoyée à {ok} utilisateurs.")

@admin_only
async def cmd_chercher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /chercher NOM ou ID")
        return
    query = " ".join(context.args)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        user_id = int(query)
        results = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchall()
    except ValueError:
        results = conn.execute("SELECT * FROM users WHERE full_name LIKE ? OR username LIKE ? LIMIT 10", (f"%{query}%", f"%{query}%")).fetchall()
    conn.close()
    if not results:
        await update.message.reply_text("❌ Aucun utilisateur trouvé.")
        return
    txt = f"🔍 *RÉSULTATS ({len(results)})*\n\n"
    for u in results:
        banni = "🚫" if u["est_banni"] else "✅"
        txt += f"{banni} *{u['full_name']}*\nID: `{u['user_id']}` | @{u['username'] or 'N/A'}\n💰 {u['solde']:.0f} FCFA\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

@admin_only
async def cmd_filleuls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /filleuls USER_ID")
        return
    try:
        parrain_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    filleuls = conn.execute("SELECT p.filleul_id, p.date_action, u.full_name, u.username FROM parrainages p LEFT JOIN users u ON p.filleul_id = u.user_id WHERE p.parrain_id = ? ORDER BY p.date_action DESC", (parrain_id,)).fetchall()
    conn.close()
    if not filleuls:
        await update.message.reply_text(f"❌ Aucun filleul pour `{parrain_id}`.", parse_mode="Markdown")
        return
    txt = f"👥 *FILLEULS DE {parrain_id} ({len(filleuls)})*\n\n"
    for f in filleuls[:20]:
        txt += f"• *{f['full_name'] or 'N/A'}* | ID: `{f['filleul_id']}`\n📅 {f['date_action'][:10] if f['date_action'] else '?'}\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown")
