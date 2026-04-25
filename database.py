import sqlite3
import os
from datetime import datetime

DB_PATH = "bot_data.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            solde       REAL DEFAULT 0,
            parrain_id  INTEGER DEFAULT NULL,
            ref_code    TEXT UNIQUE,
            date_join   TEXT,
            est_banni   INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS parrainages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            parrain_id  INTEGER,
            filleul_id  INTEGER,
            date_action TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS retraits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            methode     TEXT,
            numero      TEXT,
            pays        TEXT,
            montant     REAL,
            statut      TEXT DEFAULT 'en_attente',
            date_demande TEXT,
            date_traitement TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            action      TEXT,
            details     TEXT,
            suspect     INTEGER DEFAULT 0,
            date_action TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id     INTEGER PRIMARY KEY,
            raison      TEXT,
            date_ban    TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def create_user(user_id, username, full_name, parrain_id=None):
    import random, string
    ref_code = "REF" + ''.join(random.choices(string.digits, k=6))
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, solde, parrain_id, ref_code, date_join, est_banni)
            VALUES (?, ?, ?, 0, ?, ?, ?, 0)
        """, (user_id, username, full_name, parrain_id, ref_code, _now()))
        conn.commit()
    finally:
        conn.close()
    return ref_code

def get_solde(user_id):
    conn = get_connection()
    row = conn.execute("SELECT solde FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row["solde"] if row else 0

def update_solde(user_id, montant):
    conn = get_connection()
    conn.execute("UPDATE users SET solde = solde + ? WHERE user_id = ?", (montant, user_id))
    conn.commit()
    conn.close()

def set_solde(user_id, montant):
    conn = get_connection()
    conn.execute("UPDATE users SET solde = ? WHERE user_id = ?", (montant, user_id))
    conn.commit()
    conn.close()

def get_ref_code(user_id):
    conn = get_connection()
    row = conn.execute("SELECT ref_code FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row["ref_code"] if row else None

def get_user_by_ref(ref_code):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE ref_code = ?", (ref_code,)).fetchone()
    conn.close()
    return row

def is_banni(user_id):
    conn = get_connection()
    row = conn.execute("SELECT est_banni FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return bool(row and row["est_banni"])

def set_banni(user_id, banni, raison=""):
    conn = get_connection()
    conn.execute("UPDATE users SET est_banni = ? WHERE user_id = ?", (int(banni), user_id))
    if banni:
        conn.execute("INSERT OR REPLACE INTO blacklist VALUES (?, ?, ?)", (user_id, raison, _now()))
    else:
        conn.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT user_id FROM users WHERE est_banni = 0").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as n FROM users").fetchone()["n"]
    actifs = conn.execute("SELECT COUNT(*) as n FROM users WHERE est_banni = 0").fetchone()["n"]
    bannis = conn.execute("SELECT COUNT(*) as n FROM users WHERE est_banni = 1").fetchone()["n"]
    parrainages = conn.execute("SELECT COUNT(*) as n FROM parrainages").fetchone()["n"]
    retraits_att = conn.execute("SELECT COUNT(*) as n FROM retraits WHERE statut='en_attente'").fetchone()["n"]
    conn.close()
    return {"total": total, "actifs": actifs, "bannis": bannis,
            "parrainages": parrainages, "retraits_attente": retraits_att}

def get_blacklist():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM blacklist").fetchall()
    conn.close()
    return rows

def add_parrainage(parrain_id, filleul_id):
    conn = get_connection()
    conn.execute("INSERT INTO parrainages (parrain_id, filleul_id, date_action) VALUES (?, ?, ?)",
                 (parrain_id, filleul_id, _now()))
    conn.commit()
    conn.close()

def count_parrainages_heure(parrain_id):
    conn = get_connection()
    from datetime import datetime, timedelta
    une_heure = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute("""
        SELECT COUNT(*) as n FROM parrainages
        WHERE parrain_id = ? AND date_action > ?
    """, (parrain_id, une_heure)).fetchone()
    conn.close()
    return row["n"]

def count_filleuls(parrain_id):
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as n FROM parrainages WHERE parrain_id = ?", (parrain_id,)).fetchone()
    conn.close()
    return row["n"]

def add_retrait(user_id, methode, numero, pays, montant):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO retraits (user_id, methode, numero, pays, montant, statut, date_demande)
        VALUES (?, ?, ?, ?, ?, 'en_attente', ?)
    """, (user_id, methode, numero, pays, montant, _now()))
    retrait_id = c.lastrowid
    conn.commit()
    conn.close()
    return retrait_id

def get_retrait(retrait_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM retraits WHERE id = ?", (retrait_id,)).fetchone()
    conn.close()
    return row

def update_retrait_statut(retrait_id, statut):
    conn = get_connection()
    conn.execute("UPDATE retraits SET statut = ?, date_traitement = ? WHERE id = ?",
                 (statut, _now(), retrait_id))
    conn.commit()
    conn.close()

def add_log(user_id, action, details="", suspect=False):
    conn = get_connection()
    conn.execute("INSERT INTO logs (user_id, action, details, suspect, date_action) VALUES (?, ?, ?, ?, ?)",
                 (user_id, action, details, int(suspect), _now()))
    conn.commit()
    conn.close()

def get_logs(limit=50, suspects_only=False):
    conn = get_connection()
    if suspects_only:
        rows = conn.execute("SELECT * FROM logs WHERE suspect=1 ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows

def clear_logs():
    conn = get_connection()
    conn.execute("DELETE FROM logs")
    conn.commit()
    conn.close()

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

init_db()
