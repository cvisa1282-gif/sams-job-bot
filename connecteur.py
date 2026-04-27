from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)
from bienvenue import cmd_start, check_join_callback
from menu_buttons import (
    btn_solde, btn_parrainage, btn_retrait,
    btn_retrait_methode, btn_retrait_numero, btn_retrait_pays,
    btn_retrait_montant, btn_retrait_annuler,
    callback_valider_retrait, callback_refuser_retrait,
    RETRAIT_METHODE, RETRAIT_NUMERO, RETRAIT_PAYS, RETRAIT_MONTANT
)
from signaler import (
    btn_signaler, btn_signaler_message,
    btn_contact, btn_contact_message,
    cmd_annuler, SIGNALER_MESSAGE, CONTACT_MESSAGE
)
from admin import (
    cmd_stats, cmd_broadcast, cmd_ban, cmd_unban,
    cmd_blacklist, cmd_logs, cmd_suspects, cmd_clearlogs,
    cmd_reply, cmd_add, cmd_remove, cmd_reset,
    cmd_retraits, cmd_valider_tout, cmd_refuser_motif, cmd_paye,
    cmd_bloquer_retraits, cmd_debloquer_retraits, cmd_set_minimum,
    cmd_fraudes, cmd_doublons, cmd_ban_tel, cmd_ban_pays,
    cmd_unban_pays, cmd_liste_pays, cmd_set_limite, cmd_audit,
    cmd_broadcast_photo, cmd_programme, cmd_annonce,
    cmd_maintenance, cmd_chercher, cmd_filleuls,
    cmd_freeze, cmd_unfreeze, cmd_bonus_tous, cmd_transfert,
    cmd_retrait_notif, cmd_top_parrains, callback_bonus_top3,
    cmd_alerte_frequence, cmd_limite_horaire, cmd_liste_alertes,
    callback_sanction, cmd_autoban, cmd_reset_attempts,
    cmd_sondage, cmd_feliciter
)
from fonctions_user import btn_mes_stats, btn_objectif, btn_objectif_saisie, btn_conditions, btn_support

def register_all_handlers(application):
    application.add_handler(CommandHandler("start", cmd_start))

    retrait_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 RETRAIT$"), btn_retrait)],
        states={
            RETRAIT_METHODE: [CallbackQueryHandler(btn_retrait_methode, pattern="^methode_")],
            RETRAIT_NUMERO:  [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_retrait_numero)],
            RETRAIT_PAYS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_retrait_pays)],
            RETRAIT_MONTANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_retrait_montant)],
        },
        fallbacks=[
            CommandHandler("annuler", cmd_annuler),
            CallbackQueryHandler(btn_retrait_annuler, pattern="^retrait_annuler$"),
        ],
        allow_reentry=True
    )
    application.add_handler(retrait_conv)

    signaler_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🚨 SIGNALER$"), btn_signaler)],
        states={
            SIGNALER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_signaler_message)],
        },
        fallbacks=[CommandHandler("annuler", cmd_annuler)],
        allow_reentry=True
    )
    application.add_handler(signaler_conv)

    contact_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📩 CONTACT$"), btn_contact)],
        states={
            CONTACT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_contact_message)],
        },
        fallbacks=[CommandHandler("annuler", cmd_annuler)],
        allow_reentry=True
    )
    application.add_handler(contact_conv)

    application.add_handler(MessageHandler(filters.Regex("^💰 SOLDE$"), btn_solde))
    application.add_handler(MessageHandler(filters.Regex("^🔗 PARRAINAGE$"), btn_parrainage))
    application.add_handler(MessageHandler(filters.Regex("^📊 MES STATS$"), btn_mes_stats))
    application.add_handler(MessageHandler(filters.Regex("^🎯 OBJECTIF$"), btn_objectif))
    application.add_handler(MessageHandler(filters.Regex("^📜 CONDITIONS$"), btn_conditions))
    application.add_handler(MessageHandler(filters.Regex("^📞 SUPPORT$"), btn_support))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r"^\d+$"),
        btn_objectif_saisie
    ))

    application.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    application.add_handler(CallbackQueryHandler(callback_valider_retrait, pattern="^valider_"))
    application.add_handler(CallbackQueryHandler(callback_refuser_retrait, pattern="^refuser_"))
    application.add_handler(CallbackQueryHandler(callback_bonus_top3, pattern="^bonus_top3_"))
    application.add_handler(CallbackQueryHandler(callback_sanction, pattern="^sanction_"))

    application.add_handler(CommandHandler("stats",          cmd_stats))
    application.add_handler(CommandHandler("broadcast",      cmd_broadcast))
    application.add_handler(CommandHandler("ban",            cmd_ban))
    application.add_handler(CommandHandler("unban",          cmd_unban))
    application.add_handler(CommandHandler("blacklist",      cmd_blacklist))
    application.add_handler(CommandHandler("logs",           cmd_logs))
    application.add_handler(CommandHandler("suspects",       cmd_suspects))
    application.add_handler(CommandHandler("clearlogs",      cmd_clearlogs))
    application.add_handler(CommandHandler("reply",          cmd_reply))
    application.add_handler(CommandHandler("add",            cmd_add))
    application.add_handler(CommandHandler("remove",         cmd_remove))
    application.add_handler(CommandHandler("reset",          cmd_reset))
    application.add_handler(CommandHandler("retraits",       cmd_retraits))
    application.add_handler(CommandHandler("validertt",      cmd_valider_tout))
    application.add_handler(CommandHandler("refuser",        cmd_refuser_motif))
    application.add_handler(CommandHandler("paye",           cmd_paye))
    application.add_handler(CommandHandler("bloquertt",      cmd_bloquer_retraits))
    application.add_handler(CommandHandler("debloquertt",    cmd_debloquer_retraits))
    application.add_handler(CommandHandler("setmin",         cmd_set_minimum))
    application.add_handler(CommandHandler("fraudes",        cmd_fraudes))
    application.add_handler(CommandHandler("doublons",       cmd_doublons))
    application.add_handler(CommandHandler("bantel",         cmd_ban_tel))
    application.add_handler(CommandHandler("banpays",        cmd_ban_pays))
    application.add_handler(CommandHandler("unbanpays",      cmd_unban_pays))
    application.add_handler(CommandHandler("listepays",      cmd_liste_pays))
    application.add_handler(CommandHandler("setlimite",      cmd_set_limite))
    application.add_handler(CommandHandler("audit",          cmd_audit))
    application.add_handler(CommandHandler("broadcastphoto", cmd_broadcast_photo))
    application.add_handler(CommandHandler("programme",      cmd_programme))
    application.add_handler(CommandHandler("annonce",        cmd_annonce))
    application.add_handler(CommandHandler("maintenance",    cmd_maintenance))
    application.add_handler(CommandHandler("chercher",       cmd_chercher))
    application.add_handler(CommandHandler("filleuls",       cmd_filleuls))
    application.add_handler(CommandHandler("freeze",         cmd_freeze))
    application.add_handler(CommandHandler("unfreeze",       cmd_unfreeze))
    application.add_handler(CommandHandler("bonustous",      cmd_bonus_tous))
    application.add_handler(CommandHandler("transfert",      cmd_transfert))
    application.add_handler(CommandHandler("payenotif",      cmd_retrait_notif))
    application.add_handler(CommandHandler("topparrains",    cmd_top_parrains))
    application.add_handler(CommandHandler("alertefreq",     cmd_alerte_frequence))
    application.add_handler(CommandHandler("limitehoraire",  cmd_limite_horaire))
    application.add_handler(CommandHandler("listealertes",   cmd_liste_alertes))
    application.add_handler(CommandHandler("autoban",        cmd_autoban))
    application.add_handler(CommandHandler("resetattempts",  cmd_reset_attempts))
    application.add_handler(CommandHandler("sondage",        cmd_sondage))
    application.add_handler(CommandHandler("feliciter",      cmd_feliciter))

    print("✅ Tous les handlers enregistrés.")
