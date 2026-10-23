"""
dedup.py - Etape 3 : nettoyage des doublons

1) doublons d'URL      -> déjà bloqués à l'insertion (url_normalisee UNIQUE)
2) doublons exacts     -> même titre (hash_titre)
3) quasi-doublons      -> titres très proches (ex: dépêche AFP reprise par 5 journaux)
   on utilise TF-IDF + similarité cosinus

On ne supprime pas les quasi-doublons : on les met dans un même "groupe".
Le nombre de reprises d'une info est un indicateur intéressant pour le dashboard.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from db import get_connexion

SEUIL_SIMILARITE = 0.80


def doublons_exacts(conn):
    # on garde le plus ancien article pour chaque titre identique
    # et on note l'article gardé dans groupe_id pour compter les reprises
    cur = conn.execute("""
        UPDATE articles
        SET est_doublon = 1,
            groupe_id = (SELECT MIN(b.id) FROM articles b WHERE b.hash_titre = articles.hash_titre)
        WHERE id NOT IN (SELECT MIN(id) FROM articles GROUP BY hash_titre)
    """)
    return cur.rowcount


def quasi_doublons(conn):
    lignes = conn.execute(
        "SELECT id, titre FROM articles WHERE est_doublon = 0 ORDER BY date_pub"
    ).fetchall()
    if len(lignes) < 2:
        return 0

    ids = [l["id"] for l in lignes]
    titres = [l["titre"] for l in lignes]

    vecto = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
    matrice = vecto.fit_transform(titres)
    sim = cosine_similarity(matrice)

    groupe = {}  # id article -> id du groupe (= premier article du groupe)
    nb_doublons = 0
    for i in range(len(ids)):
        if ids[i] in groupe:
            continue
        groupe[ids[i]] = ids[i]
        for j in range(i + 1, len(ids)):
            if ids[j] not in groupe and sim[i, j] >= SEUIL_SIMILARITE:
                groupe[ids[j]] = ids[i]
                nb_doublons += 1

    for art_id, g_id in groupe.items():
        conn.execute(
            "UPDATE articles SET groupe_id = ?, est_doublon = ? WHERE id = ?",
            (g_id, 1 if art_id != g_id else 0, art_id),
        )
    return nb_doublons


def nettoyer():
    conn = get_connexion()
    conn.execute("UPDATE articles SET est_doublon = 0, groupe_id = NULL")
    a = doublons_exacts(conn)
    b = quasi_doublons(conn)
    conn.commit()
    reste = conn.execute("SELECT COUNT(*) FROM articles WHERE est_doublon = 0").fetchone()[0]
    conn.close()
    print(f"Doublons exacts : {a}")
    print(f"Quasi-doublons  : {b}")
    print(f"Articles uniques restants : {reste}")


if __name__ == "__main__":
    nettoyer()
