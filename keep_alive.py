from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "🤖 SAMS-JOB Bot est actif !"

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/health")
def health():
    return {"status": "ok", "bot": "SAMS-JOB"}, 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print(f"✅ Serveur Keep-Alive lancé sur le port {os.environ.get('PORT', 10000)}")
