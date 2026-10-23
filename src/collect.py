"""
collect.py - Etape 2 : récupérer les articles d'octobre 2026 sur les manifestations

Sources :
 - Google News (flux RSS avec une recherche par mots clés + dates)
 - flux RSS de quelques journaux français

Lancement : python src/collect.py
"""
import hashlib
import re
import time
from datetime import datetime
from urllib.parse import quote_plus, urlparse, urlunparse

import feedparser

from db import get_connexion, inserer_article

# période étudiée
DEBUT = datetime(2026, 10, 1)
FIN = datetime(2026, 11, 1)  # exclu

# mots pour garder seulement les articles qui parlent de mobilisation
MOTS_MANIF = [
    "manifestation", "manifestations", "manifestant", "manifestants",
    "grève", "grèves", "gréviste", "mobilisation", "rassemblement",
    "cortège", "intersyndicale", "blocage", "défilé", "marche",
    "colère", "protestation",
]

# recherches Google News (une requête = un flux)
REQUETES_GOOGLE = [
    "manifestation",
    "grève",
    "mobilisation syndicats",
    "intersyndicale",
    "manifestation agriculteurs",
    "grève enseignants",
    "manifestation budget",
    "rassemblement préfecture",
]

# flux RSS des journaux
FLUX_RSS = {
    "Le Monde": "https://www.lemonde.fr/societe/rss_full.xml",
    "France Info": "https://www.francetvinfo.fr/societe.rss",
    "Libération": "https://www.liberation.fr/arc/outboundfeeds/rss-all/collection/accueil-une/?outputType=xml",
    "Le Figaro": "https://www.lefigaro.fr/rss/figaro_actualite-france.xml",
    "20 Minutes": "https://www.20minutes.fr/feeds/rss-societe.xml",
    "Ouest-France": "https://www.ouest-france.fr/rss/france",
}


def url_google_news(requete):
    q = f"{requete} after:{DEBUT:%Y-%m-%d} before:{FIN:%Y-%m-%d}"
    return f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=fr&gl=FR&ceid=FR:fr"


def normaliser_url(url):
    """Enlève les paramètres de tracking (?utm=...), le # et le / final"""
    p = urlparse(url.strip())
    # Google News : on garde l'url entière car l'id est dans le chemin
    query = "" if "news.google.com" not in p.netloc else p.query
    chemin = p.path.rstrip("/")
    return urlunparse((p.scheme, p.netloc.lower(), chemin, "", query, ""))


def nettoyer_texte(txt):
    txt = re.sub(r"<[^>]+>", " ", txt or "")  # enlève le html
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def hash_titre(titre):
    t = titre.lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return hashlib.md5(t.encode("utf-8")).hexdigest()


def date_entree(entry):
    st = entry.get("published_parsed") or entry.get("updated_parsed")
    if st is None:
        return None
    return datetime(*st[:6])


def parle_de_manif(texte):
    texte = texte.lower()
    return any(mot in texte for mot in MOTS_MANIF)


def lire_flux(url, source_defaut):
    flux = feedparser.parse(url, agent="Mozilla/5.0 (projet etudiant veille media)")
    articles = []
    for e in flux.entries:
        d = date_entree(e)
        if d is None or not (DEBUT <= d < FIN):
            continue  # pas en octobre

        titre = nettoyer_texte(e.get("title", ""))
        resume = nettoyer_texte(e.get("summary", ""))

        # Google News met " - Nom du journal" à la fin du titre
        source = source_defaut
        if "source" in e and e.source.get("title"):
            source = e.source["title"]
            titre = re.sub(rf"\s+-\s+{re.escape(source)}$", "", titre)

        if not parle_de_manif(titre + " " + resume):
            continue

        articles.append({
            "titre": titre,
            "url": e.get("link", ""),
            "url_normalisee": normaliser_url(e.get("link", "")),
            "source": source,
            "date_pub": d.strftime("%Y-%m-%d %H:%M"),
            "resume": resume,
            "hash_titre": hash_titre(titre),
        })
    return articles


def collecter():
    conn = get_connexion()
    total, nouveaux = 0, 0

    tous_les_flux = [(url_google_news(r), "Google News") for r in REQUETES_GOOGLE]
    tous_les_flux += [(url, nom) for nom, url in FLUX_RSS.items()]

    for url, nom in tous_les_flux:
        try:
            articles = lire_flux(url, nom)
        except Exception as err:
            print(f"  [!] erreur sur {nom} : {err}")
            continue

        n = sum(inserer_article(conn, a) for a in articles)
        conn.commit()
        total += len(articles)
        nouveaux += n
        print(f"  {nom:12} -> {len(articles):3} articles trouvés, {n:3} nouveaux")
        time.sleep(1)  # on attend un peu pour ne pas surcharger les sites

    conn.close()
    print(f"\nFini : {total} articles lus, {nouveaux} ajoutés dans la base")


if __name__ == "__main__":
    collecter()
