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
    cmd_annuler,
    SIGNALER_MESSAGE, CONTACT_MESSAGE
)
from admin import (
    cmd_stats, cmd_broadcast, cmd_ban, cmd_unban,
    cmd_blacklist, cmd_logs, cmd_suspects, cmd_clearlogs,
    cmd_reply, cmd_add, cmd_remove, cmd_reset
)

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

    application.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    application.add_handler(CallbackQueryHandler(callback_valider_retrait, pattern="^valider_"))
    application.add_handler(CallbackQueryHandler(callback_refuser_retrait, pattern="^refuser_"))

    application.add_handler(CommandHandler("stats",      cmd_stats))
    application.add_handler(CommandHandler("broadcast",  cmd_broadcast))
    application.add_handler(CommandHandler("ban",        cmd_ban))
    application.add_handler(CommandHandler("unban",      cmd_unban))
    application.add_handler(CommandHandler("blacklist",  cmd_blacklist))
    application.add_handler(CommandHandler("logs",       cmd_logs))
    application.add_handler(CommandHandler("suspects",   cmd_suspects))
    application.add_handler(CommandHandler("clearlogs",  cmd_clearlogs))
    application.add_handler(CommandHandler("reply",      cmd_reply))
    application.add_handler(CommandHandler("add",        cmd_add))
    application.add_handler(CommandHandler("remove",     cmd_remove))
    application.add_handler(CommandHandler("reset",      cmd_reset))

    print("✅ Tous les handlers enregistrés.")
