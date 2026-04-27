import os
import pg8000
import re
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ─── CONNEXION PERSISTANTE ────────────────────────────────────────
_conn = None

def get_connection():
    global _conn
    try:
        if _conn is not None:
            _conn.run("SELECT 1")
            return _conn
    except Exception:
        _conn = None
    m = re.match(r'postgresql://(.+):(.+)@(.+):(\d+)/(.+)', DATABASE_URL)
    user, password, host, port, database = m.groups()
    _conn = pg8000.connect(
        user=user,
        password=password,
        host=host,
        port=int(port),
        database=database,
        ssl_context=True,
        timeout=10
    )
    return _conn

def exe(sql, params=()):
    conn = get_connection()
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    return c

def fetch_one(sql, params=()):
    conn = get_connection()
    c = conn.cursor()
    c.execute(sql, params)
    return c.fetchone()

def fetch_all(sql, params=()):
    conn = get_connection()
    c = conn.cursor()
    c.execute(sql, params)
    return c.fetchall()

def init_db():
    exe("""CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY, username TEXT, full_name TEXT,
        solde FLOAT DEFAULT 0, parrain_id BIGINT DEFAULT NULL,
        ref_code TEXT UNIQUE, date_join TEXT, est_banni INTEGER DEFAULT 0)""")
    exe("""CREATE TABLE IF NOT EXISTS parrainages (
        id SERIAL PRIMARY KEY, parrain_id BIGINT,
        filleul_id BIGINT, date_action TEXT)""")
    exe("""CREATE TABLE IF NOT EXISTS retraits (
        id SERIAL PRIMARY KEY, user_id BIGINT, methode TEXT,
        numero TEXT, pays TEXT, montant FLOAT,
        statut TEXT DEFAULT 'en_attente',
        date_demande TEXT, date_traitement TEXT)""")
    exe("""CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY, user_id BIGINT, action TEXT,
        details TEXT, suspect INTEGER DEFAULT 0, date_action TEXT)""")
    exe("""CREATE TABLE IF NOT EXISTS blacklist (
        user_id BIGINT PRIMARY KEY, raison TEXT, date_ban TEXT)""")
    exe("""CREATE TABLE IF NOT EXISTS blacklist_tel (
        numero TEXT PRIMARY KEY, raison TEXT, date_ban TEXT)""")
    exe("""CREATE TABLE IF NOT EXISTS blacklist_pays (
        pays TEXT PRIMARY KEY, raison TEXT, date_ban TEXT)""")
    exe("""CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY, valeur TEXT)""")
    print("✅ Base de données initialisée.")

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _row(cols, row):
    return dict(zip(cols, row)) if row else None

# ─── USERS ───────────────────────────────────────────────────────
USER_COLS = ["user_id","username","full_name","solde","parrain_id","ref_code","date_join","est_banni"]

def get_user(user_id):
    row = fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,))
    return _row(USER_COLS, row)

def create_user(user_id, username, full_name, parrain_id=None):
    import random, string
    ref_code = "REF" + ''.join(random.choices(string.digits, k=6))
    exe("""INSERT INTO users (user_id,username,full_name,solde,parrain_id,ref_code,date_join,est_banni)
        VALUES (%s,%s,%s,0,%s,%s,%s,0) ON CONFLICT (user_id) DO NOTHING""",
        (user_id, username, full_name, parrain_id, ref_code, _now()))
    return ref_code

def get_solde(user_id):
    row = fetch_one("SELECT solde FROM users WHERE user_id = %s", (user_id,))
    return row[0] if row else 0

def update_solde(user_id, montant):
    exe("UPDATE users SET solde = solde + %s WHERE user_id = %s", (montant, user_id))

def set_solde(user_id, montant):
    exe("UPDATE users SET solde = %s WHERE user_id = %s", (montant, user_id))

def get_ref_code(user_id):
    row = fetch_one("SELECT ref_code FROM users WHERE user_id = %s", (user_id,))
    return row[0] if row else None

def get_user_by_ref(ref_code):
    row = fetch_one("SELECT * FROM users WHERE ref_code = %s", (ref_code,))
    return _row(USER_COLS, row)

def is_banni(user_id):
    row = fetch_one("SELECT est_banni FROM users WHERE user_id = %s", (user_id,))
    return bool(row and row[0])

def set_banni(user_id, banni, raison=""):
    exe("UPDATE users SET est_banni = %s WHERE user_id = %s", (int(banni), user_id))
    if banni:
        exe("""INSERT INTO blacklist VALUES (%s,%s,%s)
            ON CONFLICT (user_id) DO UPDATE SET raison=%s,date_ban=%s""",
            (user_id, raison, _now(), raison, _now()))
    else:
        exe("DELETE FROM blacklist WHERE user_id = %s", (user_id,))

def get_all_users():
    rows = fetch_all("SELECT user_id FROM users WHERE est_banni = 0")
    return [r[0] for r in rows]

def get_stats():
    total = fetch_one("SELECT COUNT(*) FROM users")[0]
    actifs = fetch_one("SELECT COUNT(*) FROM users WHERE est_banni=0")[0]
    bannis = fetch_one("SELECT COUNT(*) FROM users WHERE est_banni=1")[0]
    parrainages = fetch_one("SELECT COUNT(*) FROM parrainages")[0]
    total_gains = fetch_one("SELECT COALESCE(SUM(montant),0) FROM retraits WHERE statut='valide'")[0]
    retraits_att = fetch_one("SELECT COUNT(*) FROM retraits WHERE statut='en_attente'")[0]
    actifs_7j = fetch_one("SELECT COUNT(DISTINCT user_id) FROM logs WHERE date_action > NOW() - INTERVAL '7 days'")[0]
    inscrits_today = fetch_one("SELECT COUNT(*) FROM users WHERE date_join >= CURRENT_DATE::text")[0]
    return {"total": total, "actifs": actifs, "bannis": bannis,
            "parrainages": parrainages, "retraits_attente": retraits_att,
            "total_gains": total_gains, "total_retraits": total_gains,
            "actifs_7j": actifs_7j, "inscrits_today": inscrits_today}

def get_blacklist():
    rows = fetch_all("SELECT * FROM blacklist")
    return [{"user_id": r[0], "raison": r[1], "date_ban": r[2]} for r in rows]

# ─── PARRAINAGES ─────────────────────────────────────────────────
def add_parrainage(parrain_id, filleul_id):
    exe("INSERT INTO parrainages (parrain_id,filleul_id,date_action) VALUES (%s,%s,%s)",
        (parrain_id, filleul_id, _now()))

def count_parrainages_heure(parrain_id):
    row = fetch_one("""SELECT COUNT(*) FROM parrainages
        WHERE parrain_id=%s AND date_action > NOW() - INTERVAL '1 hour'""", (parrain_id,))
    return row[0] if row else 0

def count_filleuls(parrain_id):
    row = fetch_one("SELECT COUNT(*) FROM parrainages WHERE parrain_id=%s", (parrain_id,))
    return row[0] if row else 0

# ─── RETRAITS ────────────────────────────────────────────────────
def add_retrait(user_id, methode, numero, pays, montant):
    c = exe("""INSERT INTO retraits (user_id,methode,numero,pays,montant,statut,date_demande)
        VALUES (%s,%s,%s,%s,%s,'en_attente',%s) RETURNING id""",
        (user_id, methode, numero, pays, montant, _now()))
    return c.fetchone()[0]

def get_retrait(retrait_id):
    cols = ["id","user_id","methode","numero","pays","montant","statut","date_demande","date_traitement"]
    row = fetch_one("SELECT * FROM retraits WHERE id=%s", (retrait_id,))
    return _row(cols, row)

def update_retrait_statut(retrait_id, statut):
    exe("UPDATE retraits SET statut=%s, date_traitement=%s WHERE id=%s",
        (statut, _now(), retrait_id))

def get_retraits_en_attente():
    rows = fetch_all("""SELECT r.id,r.user_id,r.methode,r.numero,r.pays,r.montant,
        r.statut,r.date_demande,u.full_name,u.username
        FROM retraits r LEFT JOIN users u ON r.user_id=u.user_id
        WHERE r.statut='en_attente' ORDER BY r.date_demande ASC""")
    cols = ["id","user_id","methode","numero","pays","montant","statut","date_demande","full_name","username"]
    return [dict(zip(cols, r)) for r in rows]

# ─── LOGS ────────────────────────────────────────────────────────
def add_log(user_id, action, details="", suspect=False):
    exe("INSERT INTO logs (user_id,action,details,suspect,date_action) VALUES (%s,%s,%s,%s,%s)",
        (user_id, action, details, int(suspect), _now()))

def get_logs(limit=50, suspects_only=False):
    if suspects_only:
        rows = fetch_all("SELECT * FROM logs WHERE suspect=1 ORDER BY id DESC LIMIT %s", (limit,))
    else:
        rows = fetch_all("SELECT * FROM logs ORDER BY id DESC LIMIT %s", (limit,))
    cols = ["id","user_id","action","details","suspect","date_action"]
    return [dict(zip(cols, r)) for r in rows]

def clear_logs():
    exe("DELETE FROM logs")

# ─── PARAMÈTRES ──────────────────────────────────────────────────
def get_parametre(cle, defaut=None):
    row = fetch_one("SELECT valeur FROM parametres WHERE cle=%s", (cle,))
    return row[0] if row else defaut

def set_parametre(cle, valeur):
    exe("INSERT INTO parametres (cle,valeur) VALUES (%s,%s) ON CONFLICT (cle) DO UPDATE SET valeur=%s",
        (cle, str(valeur), str(valeur)))

# ─── BLACKLIST ───────────────────────────────────────────────────
def is_numero_blackliste(numero):
    row = fetch_one("SELECT * FROM blacklist_tel WHERE numero=%s", (numero,))
    return row is not None

def add_numero_blacklist(numero, raison=""):
    exe("INSERT INTO blacklist_tel VALUES (%s,%s,%s) ON CONFLICT (numero) DO UPDATE SET raison=%s",
        (numero, raison, _now(), raison))

def is_pays_blackliste(pays):
    rows = fetch_all("SELECT pays FROM blacklist_pays")
    pays_lower = pays.lower()
    for row in rows:
        if row[0].lower() in pays_lower or pays_lower in row[0].lower():
            return True
    return False

def add_pays_blacklist(pays, raison=""):
    exe("INSERT INTO blacklist_pays VALUES (%s,%s,%s) ON CONFLICT (pays) DO UPDATE SET raison=%s",
        (pays, raison, _now(), raison))

def remove_pays_blacklist(pays):
    exe("DELETE FROM blacklist_pays WHERE LOWER(pays) LIKE LOWER(%s)", (f"%{pays}%",))

def get_pays_blacklist():
    rows = fetch_all("SELECT * FROM blacklist_pays")
    return [{"pays": r[0], "raison": r[1], "date_ban": r[2]} for r in rows]

init_db()
