import os
import logging
from keep_alive import keep_alive
from telegram.ext import Application
from connecteur import register_all_handlers

TOKEN    = os.environ.get("BOT_TOKEN", "8276829062:AAGYh0x34pgmZLqPVANrHlW0cRHrE2OgFow")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN manquant !")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    keep_alive()
    logger.info("🚀 Démarrage du bot SAMS-JOB...")
    application = Application.builder().token(TOKEN).build()
    register_all_handlers(application)
    logger.info("✅ Bot démarré avec succès !")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
