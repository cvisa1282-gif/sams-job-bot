from flask import Flask
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
