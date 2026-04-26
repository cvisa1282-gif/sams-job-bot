import os
import pg8000
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_connection():
    import re
    m = re.match(r'postgresql://(.+):(.+)@(.+):(\d+)/(.+)', DATABASE_URL)
    user, password, host, port, database = m.groups()
    conn = pg8000.connect(
        user=user,
        password=password,
        host=host,
        port=int(port),
        database=database,
        ssl_context=True
    )
    return conn

def dict_row(cursor, row):
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     BIGINT PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            solde       FLOAT DEFAULT 0,
            parrain_id  BIGINT DEFAULT NULL,
            ref_code    TEXT UNIQUE,
            date_join   TEXT,
            est_banni   INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS parrainages (
            id          SERIAL PRIMARY KEY,
            parrain_id  BIGINT,
            filleul_id  BIGINT,
            date_action TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS retraits (
            id               SERIAL PRIMARY KEY,
            user_id          BIGINT,
            methode          TEXT,
            numero           TEXT,
            pays             TEXT,
            montant          FLOAT,
            statut           TEXT DEFAULT 'en_attente',
            date_demande     TEXT,
            date_traitement  TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id          SERIAL PRIMARY KEY,
            user_id     BIGINT,
            action      TEXT,
            details     TEXT,
            suspect     INTEGER DEFAULT 0,
            date_action TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id     BIGINT PRIMARY KEY,
            raison      TEXT,
            date_ban    TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist_tel (
            numero      TEXT PRIMARY KEY,
            raison      TEXT,
            date_ban    TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist_pays (
            pays        TEXT PRIMARY KEY,
            raison      TEXT,
            date_ban    TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS parametres (
            cle         TEXT PRIMARY KEY,
            valeur      TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Base de données Supabase initialisée.")

def get_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        cols = ["user_id","username","full_name","solde","parrain_id","ref_code","date_join","est_banni"]
        return dict(zip(cols, row))
    return None

def create_user(user_id, username, full_name, parrain_id=None):
    import random, string
    ref_code = "REF" + ''.join(random.choices(string.digits, k=6))
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO users (user_id, username, full_name, solde, parrain_id, ref_code, date_join, est_banni)
            VALUES (%s, %s, %s, 0, %s, %s, %s, 0)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id, username, full_name, parrain_id, ref_code, _now()))
        conn.commit()
    finally:
        conn.close()
    return ref_code

def get_solde(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT solde FROM users WHERE user_id = %s", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def update_solde(user_id, montant):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET solde = solde + %s WHERE user_id = %s", (montant, user_id))
    conn.commit()
    conn.close()

def set_solde(user_id, montant):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET solde = %s WHERE user_id = %s", (montant, user_id))
    conn.commit()
    conn.close()

def get_ref_code(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT ref_code FROM users WHERE user_id = %s", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_user_by_ref(ref_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE ref_code = %s", (ref_code,))
    row = c.fetchone()
    conn.close()
    if row:
        cols = ["user_id","username","full_name","solde","parrain_id","ref_code","date_join","est_banni"]
        return dict(zip(cols, row))
    return None

def is_banni(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT est_banni FROM users WHERE user_id = %s", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])

def set_banni(user_id, banni, raison=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET est_banni = %s WHERE user_id = %s", (int(banni), user_id))
    if banni:
        c.execute("""
            INSERT INTO blacklist VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET raison=%s, date_ban=%s
        """, (user_id, raison, _now(), raison, _now()))
    else:
        c.execute("DELETE FROM blacklist WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE est_banni = 0")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE est_banni = 0")
    actifs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE est_banni = 1")
    bannis = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM parrainages")
    parrainages = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(montant),0) FROM retraits WHERE statut='valide'")
    total_gains = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM retraits WHERE statut='en_attente'")
    retraits_att = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM logs WHERE date_action > NOW() - INTERVAL '7 days'")
    actifs_7j = c.fetchone()[0]
    conn.close()
    return {
        "total": total, "actifs": actifs, "bannis": bannis,
        "parrainages": parrainages, "retraits_attente": retraits_att,
        "total_gains": total_gains, "total_retraits": total_gains,
        "actifs_7j": actifs_7j
    }

def get_blacklist():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM blacklist")
    rows = c.fetchall()
    conn.close()
    return [{"user_id": r[0], "raison": r[1], "date_ban": r[2]} for r in rows]

def add_parrainage(parrain_id, filleul_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO parrainages (parrain_id, filleul_id, date_action) VALUES (%s, %s, %s)",
              (parrain_id, filleul_id, _now()))
    conn.commit()
    conn.close()

def count_parrainages_heure(parrain_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM parrainages
        WHERE parrain_id = %s
        AND date_action > NOW() - INTERVAL '1 hour'
    """, (parrain_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def count_filleuls(parrain_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM parrainages WHERE parrain_id = %s", (parrain_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def add_retrait(user_id, methode, numero, pays, montant):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO retraits (user_id, methode, numero, pays, montant, statut, date_demande)
        VALUES (%s, %s, %s, %s, %s, 'en_attente', %s)
        RETURNING id
    """, (user_id, methode, numero, pays, montant, _now()))
    retrait_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return retrait_id

def get_retrait(retrait_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM retraits WHERE id = %s", (retrait_id,))
    row = c.fetchone()
    conn.close()
    if row:
        cols = ["id","user_id","methode","numero","pays","montant","statut","date_demande","date_traitement"]
        return dict(zip(cols, row))
    return None

def update_retrait_statut(retrait_id, statut):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE retraits SET statut = %s, date_traitement = %s WHERE id = %s",
              (statut, _now(), retrait_id))
    conn.commit()
    conn.close()

def get_retraits_en_attente():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.user_id, r.methode, r.numero, r.pays, r.montant,
               r.statut, r.date_demande, u.full_name, u.username
        FROM retraits r
        LEFT JOIN users u ON r.user_id = u.user_id
        WHERE r.statut = 'en_attente'
        ORDER BY r.date_demande ASC
    """)
    rows = c.fetchall()
    conn.close()
    cols = ["id","user_id","methode","numero","pays","montant","statut","date_demande","full_name","username"]
    return [dict(zip(cols, r)) for r in rows]

def add_log(user_id, action, details="", suspect=False):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action, details, suspect, date_action) VALUES (%s, %s, %s, %s, %s)",
              (user_id, action, details, int(suspect), _now()))
    conn.commit()
    conn.close()

def get_logs(limit=50, suspects_only=False):
    conn = get_connection()
    c = conn.cursor()
    if suspects_only:
        c.execute("SELECT * FROM logs WHERE suspect=1 ORDER BY id DESC LIMIT %s", (limit,))
    else:
        c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT %s", (limit,))
    rows = c.fetchall()
    conn.close()
    cols = ["id","user_id","action","details","suspect","date_action"]
    return [dict(zip(cols, r)) for r in rows]

def clear_logs():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM logs")
    conn.commit()
    conn.close()

def get_parametre(cle, defaut=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT valeur FROM parametres WHERE cle = %s", (cle,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else defaut

def set_parametre(cle, valeur):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO parametres (cle, valeur) VALUES (%s, %s)
        ON CONFLICT (cle) DO UPDATE SET valeur = %s
    """, (cle, str(valeur), str(valeur)))
    conn.commit()
    conn.close()

def is_numero_blackliste(numero):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM blacklist_tel WHERE numero = %s", (numero,))
    row = c.fetchone()
    conn.close()
    return row is not None

def add_numero_blacklist(numero, raison=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO blacklist_tel VALUES (%s, %s, %s)
        ON CONFLICT (numero) DO UPDATE SET raison=%s
    """, (numero, raison, _now(), raison))
    conn.commit()
    conn.close()

def is_pays_blackliste(pays):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT pays FROM blacklist_pays")
    rows = c.fetchall()
    conn.close()
    pays_lower = pays.lower()
    for row in rows:
        if row[0].lower() in pays_lower or pays_lower in row[0].lower():
            return True
    return False

def add_pays_blacklist(pays, raison=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO blacklist_pays VALUES (%s, %s, %s)
        ON CONFLICT (pays) DO UPDATE SET raison=%s
    """, (pays, raison, _now(), raison))
    conn.commit()
    conn.close()

def remove_pays_blacklist(pays):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM blacklist_pays WHERE LOWER(pays) LIKE LOWER(%s)", (f"%{pays}%",))
    conn.commit()
    conn.close()

def get_pays_blacklist():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM blacklist_pays")
    rows = c.fetchall()
    conn.close()
    return [{"pays": r[0], "raison": r[1], "date_ban": r[2]} for r in rows]

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

init_db()
