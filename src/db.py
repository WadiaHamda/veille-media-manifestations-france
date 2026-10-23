"""
db.py - connexion à la base SQLite + petites fonctions utiles
"""
import sqlite3
from pathlib import Path

# chemins du projet
RACINE = Path(__file__).resolve().parent.parent
DB_PATH = RACINE / "data" / "veille.db"
SCHEMA_PATH = RACINE / "sql" / "schema.sql"


def get_connexion():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def creer_base():
    """Etape 1 : on crée les tables à partir du fichier schema.sql"""
    conn = get_connexion()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Base créée : {DB_PATH}")


def inserer_article(conn, article):
    """Insère un article. Renvoie True si il est nouveau, False si l'url existe déja."""
    try:
        conn.execute(
            """INSERT INTO articles (titre, url, url_normalisee, source, date_pub, resume, hash_titre)
               VALUES (:titre, :url, :url_normalisee, :source, :date_pub, :resume, :hash_titre)""",
            article,
        )
        return True
    except sqlite3.IntegrityError:
        # url_normalisee est UNIQUE donc doublon d'url -> on ignore
        return False


if __name__ == "__main__":
    creer_base()
