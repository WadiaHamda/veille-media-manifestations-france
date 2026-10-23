"""
enrich.py - Etape 3 bis : on analyse chaque article pour trouver
  - les villes citées
  - les thèmes
  - les signaux (ce qui peut annoncer une décision politique)

Méthode simple à base de règles / mots clés : facile à expliquer et à vérifier.
(amélioration possible : spaCy pour les entités, ou un modèle de classification)
"""
import re
import unicodedata

from db import get_connexion

# ---------------------------------------------------------------
# Définition des signaux
# chaque type a une liste de motifs (regex) et un poids (importance)
# ---------------------------------------------------------------
SIGNAUX = {
    "appel_mobilisation": {
        "poids": 0.9,
        "motifs": [r"appel(le|lent)? à (la )?(grève|manifester|mobilisation)",
                   r"journée de (mobilisation|grève|action)",
                   r"grève reconductible", r"préavis de grève",
                   r"appellent à", r"nouvelle (journée|date) de mobilisation"],
    },
    "syndicat": {
        "poids": 0.6,
        "motifs": [r"intersyndicale", r"\bcgt\b", r"\bcfdt\b", r"force ouvrière|\bfo\b",
                   r"\bunsa\b", r"sud[- ]rail|solidaires", r"\bfsu\b", r"\bfnsea\b", r"coordination rurale"],
    },
    "reaction_politique": {
        "poids": 1.0,
        "motifs": [r"49[\.,]3", r"motion de censure", r"premier ministre", r"ministre",
                   r"gouvernement", r"assemblée nationale", r"sénat", r"amendement",
                   r"projet de loi", r"élysée", r"macron", r"recul", r"concession"],
    },
    "violences": {
        "poids": 0.7,
        "motifs": [r"interpellations?", r"heurts", r"affrontements?", r"gaz lacrymogène",
                   r"black bloc", r"blessés?", r"gardes? à vue", r"dégradations?"],
    },
    "ampleur": {
        "poids": 0.8,
        "motifs": [r"\d[\d\s]* ?(000|mille) (manifestants|personnes)",
                   r"selon la cgt", r"selon (le ministère|la préfecture|la police)",
                   r"forte mobilisation", r"record"],
    },
}


def sans_accents(txt):
    return "".join(c for c in unicodedata.normalize("NFD", txt)
                   if unicodedata.category(c) != "Mn")


def trouver_villes(texte, villes):
    trouvees = []
    for v in villes:
        # \b ne marche pas bien avec les tirets, donc on fait notre propre limite
        motif = r"(?<![\w-])" + re.escape(v["nom"].lower()) + r"(?![\w-])"
        if re.search(motif, texte):
            trouvees.append(v["id"])
    return trouvees


def trouver_themes(texte, themes):
    res = []
    texte_sa = sans_accents(texte)
    for t in themes:
        score = 0
        for mot in t["mots_cles"].split(","):
            mot = sans_accents(mot.strip().lower())
            if mot and re.search(r"(?<!\w)" + re.escape(mot) + r"(?!\w)", texte_sa):
                score += 1
        if score > 0:
            res.append((t["id"], score))
    return res


def trouver_signaux(texte):
    res = []
    for type_signal, conf in SIGNAUX.items():
        trouves = []
        for motif in conf["motifs"]:
            m = re.search(motif, texte)
            if m:
                trouves.append(m.group(0))
        if trouves:
            # plus on trouve d'indices, plus le signal est fort (max = poids)
            intensite = round(conf["poids"] * min(1, 0.5 + 0.25 * len(trouves)), 2)
            res.append((type_signal, intensite, ", ".join(trouves)))
    return res


def enrichir():
    conn = get_connexion()
    villes = conn.execute("SELECT id, nom FROM villes").fetchall()
    themes = conn.execute("SELECT id, mots_cles FROM themes").fetchall()

    # on recommence à zéro à chaque lancement
    conn.execute("DELETE FROM article_ville")
    conn.execute("DELETE FROM article_theme")
    conn.execute("DELETE FROM signal")

    articles = conn.execute(
        "SELECT id, titre, resume FROM articles WHERE est_doublon = 0"
    ).fetchall()

    for a in articles:
        texte = f"{a['titre']} {a['resume'] or ''}".lower()

        for v_id in trouver_villes(texte, villes):
            conn.execute("INSERT OR IGNORE INTO article_ville VALUES (?, ?)", (a["id"], v_id))

        for t_id, score in trouver_themes(texte, themes):
            conn.execute("INSERT OR IGNORE INTO article_theme VALUES (?, ?, ?)", (a["id"], t_id, score))

        for type_s, intensite, desc in trouver_signaux(texte):
            conn.execute(
                "INSERT INTO signal (article_id, type, intensite, description) VALUES (?, ?, ?, ?)",
                (a["id"], type_s, intensite, desc),
            )

    conn.commit()
    for table in ["article_ville", "article_theme", "signal"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:14} : {n} lignes")
    conn.close()


if __name__ == "__main__":
    enrichir()
