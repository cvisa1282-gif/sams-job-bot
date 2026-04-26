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

# ─── ADMIN 4 : FREEZE/UNFREEZE ───────────────────────────────────
@admin_only
async def cmd_freeze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /freeze USER_ID raison")
        return
    try:
        user_id = int(context.args[0])
        raison = " ".join(context.args[1:]) or "Compte gelé temporairement"
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    set_parametre(f"freeze_{user_id}", "1")
    set_parametre(f"freeze_raison_{user_id}", raison)
    log_action(user_id, "FREEZE", raison)
    await update.message.reply_text(f"🧊 Compte `{user_id}` gelé.\nRaison : {raison}", parse_mode="Markdown")
    try:
        await context.bot.send_message(
            user_id,
            f"🧊 *Votre compte est temporairement gelé*\n\n"
            f"📝 Raison : _{raison}_\n\n"
            f"Contactez l'administrateur pour plus d'informations.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

@admin_only
async def cmd_unfreeze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /unfreeze USER_ID")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    set_parametre(f"freeze_{user_id}", "0")
    log_action(user_id, "UNFREEZE", "Compte dégelé")
    await update.message.reply_text(f"✅ Compte `{user_id}` dégelé.", parse_mode="Markdown")
    try:
        await context.bot.send_message(
            user_id,
            "✅ *Votre compte a été dégelé !*\n\nVous pouvez à nouveau utiliser toutes les fonctions.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

# ─── ADMIN 5 : BONUS TOUS ─────────────────────────────────────────
@admin_only
async def cmd_bonus_tous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /bonustous MONTANT")
        return
    try:
        montant = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Montant invalide.")
        return
    users = get_all_users()
    ok = 0
    for uid in users:
        try:
            update_solde(uid, montant)
            await context.bot.send_message(
                uid,
                f"🎁 *BONUS SURPRISE !*\n\n"
                f"💰 +*{montant:.0f} FCFA* viennent d'être ajoutés à votre solde !\n\n"
                f"🎊 Cadeau de l'administrateur. Merci de votre fidélité !",
                parse_mode="Markdown"
            )
            ok += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Bonus de {montant:.0f} FCFA envoyé à {ok} utilisateurs.")

# ─── ADMIN 13 : TRANSFERT ─────────────────────────────────────────
@admin_only
async def cmd_transfert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Usage : /transfert ID1 ID2 MONTANT\n(Transfère de ID1 vers ID2)")
        return
    try:
        id1 = int(context.args[0])
        id2 = int(context.args[1])
        montant = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Paramètres invalides.")
        return
    solde1 = get_solde(id1)
    if solde1 < montant:
        await update.message.reply_text(f"❌ Solde insuffisant pour `{id1}` ({solde1:.0f} FCFA).", parse_mode="Markdown")
        return
    update_solde(id1, -montant)
    update_solde(id2, montant)
    log_action(id1, "TRANSFERT_DEBIT", f"-{montant} FCFA vers {id2}")
    log_action(id2, "TRANSFERT_CREDIT", f"+{montant} FCFA de {id1}")
    await update.message.reply_text(
        f"✅ Transfert effectué !\n`{id1}` → `{id2}` : *{montant:.0f} FCFA*",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(id1, f"💸 *{montant:.0f} FCFA* ont été transférés de votre compte.", parse_mode="Markdown")
        await context.bot.send_message(id2, f"💰 *+{montant:.0f} FCFA* ont été ajoutés à votre compte.", parse_mode="Markdown")
    except Exception:
        pass

# ─── ADMIN 17 : RETRAIT AVEC NOTIFICATION ────────────────────────
@admin_only
async def cmd_retrait_notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valider un retrait et notifier avec message personnalisé"""
    if len(context.args) < 2:
        await update.message.reply_text("Usage : /payenotif RETRAIT_ID message_pour_user")
        return
    try:
        retrait_id = int(context.args[0])
        message = " ".join(context.args[1:])
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
    update_retrait_statut(retrait_id, "paye")
    log_action(r["user_id"], "RETRAIT_PAYE_NOTIF", f"{r['montant']} FCFA")
    await update.message.reply_text(f"✅ Retrait #{retrait_id} marqué payé avec notification.")
    try:
        await context.bot.send_message(
            r["user_id"],
            f"💸 *RETRAIT EFFECTUÉ*\n\n"
            f"✅ Votre retrait de *{r['montant']:.0f} FCFA* a été envoyé !\n\n"
            f"📝 Message de l'admin :\n_{message}_\n\n"
            f"Merci de votre confiance ! 🙏",
            parse_mode="Markdown"
        )
    except Exception:
        pass

# ─── ADMIN 24 : TOP PARRAINS + BONUS VIP ────────────────────────
@admin_only
async def cmd_top_parrains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    top = conn.execute("""
        SELECT p.parrain_id, COUNT(*) as nb, u.full_name, u.username, u.solde
        FROM parrainages p
        LEFT JOIN users u ON p.parrain_id = u.user_id
        GROUP BY p.parrain_id
        ORDER BY nb DESC LIMIT 20
    """).fetchall()
    conn.close()
    if not top:
        await update.message.reply_text("❌ Aucun parrainage.")
        return
    txt = "🏆 *TOP 20 PARRAINS*\n\n"
    medailles = ["🥇","🥈","🥉"]
    for i, row in enumerate(top):
        med = medailles[i] if i < 3 else f"{i+1}."
        txt += f"{med} *{row['full_name'] or 'N/A'}* (`{row['parrain_id']}`)\n👥 {row['nb']} filleuls | 💰 {row['solde']:.0f} FCFA\n\n"
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("💰 Bonus argent au Top 3", callback_data="bonus_top3_argent")],
        [InlineKeyboardButton("🔗 Lien VIP au Top 3", callback_data="bonus_top3_lien")]
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def callback_bonus_top3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Accès refusé.", show_alert=True)
        return
    await query.answer()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    top3 = conn.execute("""
        SELECT p.parrain_id, COUNT(*) as nb, u.full_name
        FROM parrainages p
        LEFT JOIN users u ON p.parrain_id = u.user_id
        GROUP BY p.parrain_id
        ORDER BY nb DESC LIMIT 3
    """).fetchall()
    conn.close()

    bonus_montants = [5000, 3000, 1000]

    if query.data == "bonus_top3_argent":
        for i, row in enumerate(top3):
            montant = bonus_montants[i]
            update_solde(row["parrain_id"], montant)
            log_action(row["parrain_id"], "BONUS_TOP3", f"+{montant} FCFA")
            try:
                await context.bot.send_message(
                    row["parrain_id"],
                    f"🏆 *RÉCOMPENSE TOP PARRAIN !*\n\n"
                    f"Félicitations ! Vous êtes classé *#{i+1}* des meilleurs parrains !\n\n"
                    f"💰 *+{montant} FCFA* ajoutés à votre solde !\n\n"
                    f"🎊 Continuez comme ça !",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        await query.edit_message_text(f"✅ Bonus argent envoyé au Top 3 !\n🥇 +5000 | 🥈 +3000 | 🥉 +1000 FCFA")

    elif query.data == "bonus_top3_lien":
        import random, string
        for i, row in enumerate(top3):
            code_vip = "VIP" + ''.join(random.choices(string.digits, k=6))
            set_parametre(f"lien_vip_{code_vip}", str(row["parrain_id"]))
            set_parametre(f"bonus_vip_{code_vip}", "500")
            lien_vip = f"https://t.me/{os.environ.get('BOT_USERNAME', 'votre_bot')}?start={code_vip}"
            log_action(row["parrain_id"], "LIEN_VIP", f"Code: {code_vip}")
            try:
                await context.bot.send_message(
                    row["parrain_id"],
                    f"👑 *LIEN VIP EXCLUSIF !*\n\n"
                    f"Félicitations ! Vous êtes classé *#{i+1}* des meilleurs parrains !\n\n"
                    f"🔗 Votre lien VIP spécial :\n`{lien_vip}`\n\n"
                    f"💰 Chaque ami inscrit via ce lien = *+500 FCFA* pour vous !\n"
                    f"👁 Ce lien est visible par tous comme lien d'élite !",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        users = get_all_users()
        for uid in users:
            try:
                await context.bot.send_message(
                    uid,
                    f"🏆 *NOS TOP PARRAINS ONT ÉTÉ RÉCOMPENSÉS !*\n\n"
                    f"Les meilleurs parrains du mois ont reçu des liens VIP exclusifs !\n\n"
                    f"💪 Parrainez plus pour faire partie du top !",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        await query.edit_message_text("✅ Liens VIP envoyés au Top 3 et tous les utilisateurs notifiés !")

# ─── ADMIN 31 : ALERTE FRÉQUENCE ─────────────────────────────────
@admin_only
async def cmd_alerte_frequence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /alertefreq USER_ID")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    actions = conn.execute("""
        SELECT action, COUNT(*) as nb, MIN(date_action) as debut, MAX(date_action) as fin
        FROM logs WHERE user_id = ?
        AND date_action > datetime('now', '-24 hours')
        GROUP BY action ORDER BY nb DESC
    """, (user_id,)).fetchall()
    conn.close()
    if not actions:
        await update.message.reply_text(f"✅ Aucune activité suspecte pour `{user_id}`.", parse_mode="Markdown")
        return
    txt = f"⚡ *FRÉQUENCE D'ACTIONS — `{user_id}`*\n\n"
    for a in actions:
        txt += f"• {a['action']} : *{a['nb']} fois* en 24h\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

# ─── ADMIN 32 : LIMITE HORAIRE ────────────────────────────────────
@admin_only
async def cmd_limite_horaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        actuel = get_parametre("limite_horaire_globale", "Non définie")
        await update.message.reply_text(
            f"💰 Limite horaire actuelle : *{actuel} FCFA*\n\nUsage : /limitehoraire MONTANT",
            parse_mode="Markdown"
        )
        return
    try:
        montant = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Montant invalide.")
        return
    set_parametre("limite_horaire_globale", str(montant))
    await update.message.reply_text(f"✅ Limite horaire globale fixée à *{montant:.0f} FCFA*.", parse_mode="Markdown")

# ─── ADMIN 34 : LISTE ALERTES + SANCTIONS ───────────────────────
@admin_only
async def cmd_liste_alertes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    suspects = conn.execute("""
        SELECT user_id, COUNT(*) as nb, MAX(date_action) as derniere
        FROM logs WHERE suspect = 1
        GROUP BY user_id ORDER BY nb DESC LIMIT 15
    """).fetchall()
    conn.close()
    if not suspects:
        await update.message.reply_text("✅ Aucune alerte active.")
        return
    txt = "🚨 *LISTE DES UTILISATEURS EN ALERTE*\n\n"
    for s in suspects:
        txt += f"• `{s['user_id']}` — {s['nb']} alertes | Dernière : {s['derniere'][:16]}\n"
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("💸 Sanctionner (retrait solde)", callback_data="sanction_retrait")],
        [InlineKeyboardButton("🔒 Sanctionner (bloquer retraits)", callback_data="sanction_bloquer")],
        [InlineKeyboardButton("🧊 Sanctionner (geler solde)", callback_data="sanction_geler")]
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def callback_sanction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Accès refusé.", show_alert=True)
        return
    await query.answer()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    suspects = conn.execute("""
        SELECT user_id, COUNT(*) as nb FROM logs
        WHERE suspect = 1 GROUP BY user_id ORDER BY nb DESC LIMIT 15
    """).fetchall()
    conn.close()

    if query.data == "sanction_retrait":
        for s in suspects:
            uid = s["user_id"]
            solde = get_solde(uid)
            penalite = min(solde, solde * 0.5)
            if penalite > 0:
                update_solde(uid, -penalite)
                log_action(uid, "SANCTION_RETRAIT", f"-{penalite:.0f} FCFA")
                try:
                    await context.bot.send_message(uid, f"⚠️ *SANCTION*\n\nActivité suspecte détectée.\n💸 *{penalite:.0f} FCFA* retirés de votre solde.", parse_mode="Markdown")
                except Exception:
                    pass
        await query.edit_message_text("✅ Sanction retrait appliquée à tous les suspects.")

    elif query.data == "sanction_bloquer":
        for s in suspects:
            uid = s["user_id"]
            set_parametre(f"retraits_bloques_user_{uid}", "1")
            log_action(uid, "SANCTION_BLOCAGE", "Retraits bloqués")
            try:
                await context.bot.send_message(uid, "⚠️ *SANCTION*\n\nVos retraits ont été temporairement bloqués suite à une activité suspecte.", parse_mode="Markdown")
            except Exception:
                pass
        await query.edit_message_text("✅ Retraits bloqués pour tous les suspects.")

    elif query.data == "sanction_geler":
        for s in suspects:
            uid = s["user_id"]
            set_parametre(f"freeze_{uid}", "1")
            set_parametre(f"freeze_raison_{uid}", "Activité suspecte détectée")
            log_action(uid, "SANCTION_GEL", "Solde gelé")
            try:
                await context.bot.send_message(uid, "🧊 *SANCTION*\n\nVotre solde a été gelé suite à une activité suspecte.\nContactez l'administrateur.", parse_mode="Markdown")
            except Exception:
                pass
        await query.edit_message_text("✅ Soldes gelés pour tous les suspects.")

# ─── ADMIN 35 : AUTOBAN ──────────────────────────────────────────
@admin_only
async def cmd_autoban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        seuil = get_parametre("autoban_seuil", "Non défini")
        await update.message.reply_text(
            f"🤖 Seuil autoban actuel : *{seuil} alertes*\n\nUsage : /autoban SEUIL\nExemple : /autoban 10",
            parse_mode="Markdown"
        )
        return
    try:
        seuil = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Seuil invalide.")
        return
    set_parametre("autoban_seuil", str(seuil))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    suspects = conn.execute("""
        SELECT user_id, COUNT(*) as nb FROM logs
        WHERE suspect = 1 GROUP BY user_id HAVING nb >= ?
    """, (seuil,)).fetchall()
    conn.close()
    banni_count = 0
    for s in suspects:
        uid = s["user_id"]
        if not is_banni(uid):
            set_banni(uid, True, f"AutoBan : {s['nb']} alertes")
            log_action(uid, "AUTOBAN", f"{s['nb']} alertes")
            banni_count += 1
            try:
                await context.bot.send_message(uid, "🚫 Votre compte a été suspendu automatiquement.")
            except Exception:
                pass
    await update.message.reply_text(
        f"✅ Seuil autoban fixé à *{seuil}* alertes.\n"
        f"🚫 *{banni_count}* comptes bannis automatiquement.",
        parse_mode="Markdown"
    )

# ─── ADMIN 38 : RESET TENTATIVES ─────────────────────────────────
@admin_only
async def cmd_reset_attempts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /resetattempts USER_ID")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM logs WHERE user_id = ? AND suspect = 1", (user_id,))
    conn.commit()
    conn.close()
    log_action(user_id, "RESET_ATTEMPTS", "Alertes effacées par admin")
    await update.message.reply_text(f"✅ Tentatives suspectes de `{user_id}` remises à zéro.", parse_mode="Markdown")

# ─── ADMIN 44 : SONDAGE ──────────────────────────────────────────
@admin_only
async def cmd_sondage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage : /sondage question option1 option2\n"
            "Exemple : /sondage 'Aimez-vous le bot?' Oui Non"
        )
        return
    question = context.args[0]
    options = context.args[1:]
    users = get_all_users()
    ok = 0
    for uid in users:
        try:
            await context.bot.send_poll(
                uid,
                question,
                options,
                is_anonymous=True
            )
            ok += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Sondage envoyé à {ok} utilisateurs.")

# ─── ADMIN 46 : FÉLICITER ─────────────────────────────────────────
@admin_only
async def cmd_feliciter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /feliciter USER_ID raison")
        return
    try:
        user_id = int(context.args[0])
        raison = " ".join(context.args[1:]) or "Excellente performance !"
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    try:
        await context.bot.send_message(
            user_id,
            f"🎊 *FÉLICITATIONS !*\n\n"
            f"L'administrateur vous félicite !\n\n"
            f"🏅 _{raison}_\n\n"
            f"Continuez comme ça, vous êtes sur la bonne voie ! 💪",
            parse_mode="Markdown"
        )
        await update.message.reply_text(f"✅ Félicitations envoyées à `{user_id}`.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {e}")
