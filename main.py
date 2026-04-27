import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from telegram.ext import Application
from connecteur import register_all_handlers

TOKEN    = os.environ.get("BOT_TOKEN", "8276829062:AAGYh0x34pgmZLqPVANrHlW0cRHrE2OgFow")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6610074482"))
PORT     = int(os.environ.get("PORT", 10000))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🤖 SAMS-JOB Bot est actif !"

@flask_app.route("/ping")
def ping():
    return "pong", 200

@flask_app.route("/health")
def health():
    return {"status": "ok"}, 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

def run_bot():
    async def start():
        app = Application.builder().token(TOKEN).build()
        register_all_handlers(app)
        logger.info("✅ Bot démarré avec succès !")
        await app.initialize()
        await app.start()
        await app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        await asyncio.Event().wait()
    asyncio.run(start())

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"✅ Serveur Flask lancé sur le port {PORT}")
    run_bot()
