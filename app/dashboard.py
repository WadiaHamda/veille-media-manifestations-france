"""
dashboard.py - Etape 4 : tableau de bord interactif
Lancement : streamlit run app/dashboard.py
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from db import DB_PATH  # noqa: E402

st.set_page_config(page_title="Veille manifestations - Octobre 2026", layout="wide")

NOMS_SIGNAUX = {
    "appel_mobilisation": "Appel à la mobilisation",
    "syndicat": "Syndicats impliqués",
    "reaction_politique": "Réaction politique",
    "violences": "Violences / interpellations",
    "ampleur": "Ampleur du mouvement",
}


# ------------------------------------------------------------
# Chargement des données
# ------------------------------------------------------------
@st.cache_data(ttl=600)
def charger():
    conn = sqlite3.connect(DB_PATH)
    articles = pd.read_sql("""
        SELECT a.id, a.titre, a.url, a.source, a.date_pub, a.resume,
               (SELECT COUNT(*) FROM articles b WHERE b.groupe_id = a.id) AS reprises
        FROM articles a WHERE a.est_doublon = 0
    """, conn, parse_dates=["date_pub"])
    themes = pd.read_sql("""
        SELECT at.article_id, t.libelle AS theme
        FROM article_theme at JOIN themes t ON t.id = at.theme_id
    """, conn)
    villes = pd.read_sql("""
        SELECT av.article_id, v.nom AS ville, v.region, v.latitude, v.longitude
        FROM article_ville av JOIN villes v ON v.id = av.ville_id
    """, conn)
    signaux = pd.read_sql("SELECT article_id, type, intensite, description FROM signal", conn)
    conn.close()
    articles["jour"] = articles["date_pub"].dt.date
    signaux["type_lisible"] = signaux["type"].map(NOMS_SIGNAUX)
    return articles, themes, villes, signaux


if not DB_PATH.exists():
    st.error("La base n'existe pas encore. Lance d'abord : python src/pipeline.py")
    st.stop()

articles, themes, villes, signaux = charger()

if articles.empty:
    st.warning("Aucun article dans la base. Lance la collecte d'abord.")
    st.stop()

# ------------------------------------------------------------
# Filtres (barre latérale)
# ------------------------------------------------------------
st.sidebar.header("Filtres")

jmin, jmax = articles["jour"].min(), articles["jour"].max()
periode = st.sidebar.date_input("Période", (jmin, jmax), min_value=jmin, max_value=jmax)
choix_sources = st.sidebar.multiselect("Sources", sorted(articles["source"].dropna().unique()))
choix_themes = st.sidebar.multiselect("Thèmes", sorted(themes["theme"].unique()))
choix_regions = st.sidebar.multiselect("Régions", sorted(villes["region"].unique()))
choix_signaux = st.sidebar.multiselect("Type de signal", list(NOMS_SIGNAUX.values()))

df = articles.copy()
if isinstance(periode, tuple) and len(periode) == 2:
    df = df[(df["jour"] >= periode[0]) & (df["jour"] <= periode[1])]
if choix_sources:
    df = df[df["source"].isin(choix_sources)]
if choix_themes:
    df = df[df["id"].isin(themes[themes["theme"].isin(choix_themes)]["article_id"])]
if choix_regions:
    df = df[df["id"].isin(villes[villes["region"].isin(choix_regions)]["article_id"])]
if choix_signaux:
    df = df[df["id"].isin(signaux[signaux["type_lisible"].isin(choix_signaux)]["article_id"])]

ids = set(df["id"])
th = themes[themes["article_id"].isin(ids)]
vi = villes[villes["article_id"].isin(ids)]
sg = signaux[signaux["article_id"].isin(ids)]

# ------------------------------------------------------------
# En-tête + KPI
# ------------------------------------------------------------
st.title("📰 Veille média : manifestations en France")
st.caption("Octobre 2026 · analyse automatique des articles publiés")

signaux_forts = sg[sg["intensite"] >= 0.75]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Articles analysés", len(df))
c2.metric("Villes concernées", vi["ville"].nunique())
c3.metric("Signaux forts", signaux_forts["article_id"].nunique())
c4.metric("Thème dominant", th["theme"].value_counts().idxmax() if not th.empty else "-")

# ------------------------------------------------------------
# Evolution dans le temps + détection des pics
# ------------------------------------------------------------
st.subheader("Évolution du nombre d'articles")

par_jour = df.groupby("jour").size().rename("articles").reset_index()
moy, ecart = par_jour["articles"].mean(), par_jour["articles"].std()
seuil = moy + 2 * (ecart if pd.notna(ecart) else 0)
par_jour["pic"] = par_jour["articles"] > seuil

fig = px.bar(par_jour, x="jour", y="articles",
             color=par_jour["pic"].map({True: "Pic anormal", False: "Normal"}),
             color_discrete_map={"Pic anormal": "#d62728", "Normal": "#4c78a8"},
             labels={"jour": "", "articles": "Articles", "color": ""})
fig.add_hline(y=seuil, line_dash="dot", annotation_text="seuil d'alerte (moyenne + 2 écarts-types)")
st.plotly_chart(fig, width="stretch")

pics = par_jour[par_jour["pic"]]
if not pics.empty:
    st.info("Pics détectés : " + ", ".join(d.strftime("%d/%m") for d in pics["jour"]))

# ------------------------------------------------------------
# Carte + thèmes
# ------------------------------------------------------------
col_g, col_d = st.columns(2)

with col_g:
    st.subheader("Carte des villes citées")
    carte = vi.groupby(["ville", "latitude", "longitude"]).size().rename("mentions").reset_index()
    if carte.empty:
        st.write("Pas de ville trouvée.")
    else:
        fig = px.scatter_map(carte, lat="latitude", lon="longitude", size="mentions",
                             hover_name="ville", size_max=40, zoom=4.3,
                             center={"lat": 46.6, "lon": 2.4}, height=480,
                             map_style="carto-positron")
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width="stretch")

with col_d:
    st.subheader("Thèmes des mobilisations")
    cpt = th["theme"].value_counts().reset_index()
    cpt.columns = ["theme", "articles"]
    fig = px.bar(cpt.sort_values("articles"), x="articles", y="theme", orientation="h",
                 labels={"theme": "", "articles": "Articles"}, height=480)
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------
# Thèmes au fil du temps
# ------------------------------------------------------------
st.subheader("Thèmes au fil des jours")
tt = th.merge(df[["id", "jour"]], left_on="article_id", right_on="id")
tt = tt.groupby(["jour", "theme"]).size().rename("articles").reset_index()
if not tt.empty:
    fig = px.line(tt, x="jour", y="articles", color="theme", markers=True,
                  labels={"jour": "", "articles": "Articles", "theme": "Thème"})
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------
# Signaux
# ------------------------------------------------------------
st.subheader("Signaux détectés")
col_a, col_b = st.columns([1, 2])

with col_a:
    rep = sg["type_lisible"].value_counts().reset_index()
    rep.columns = ["signal", "articles"]
    fig = px.pie(rep, names="signal", values="articles", hole=0.45)
    fig.update_layout(legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")

with col_b:
    # score d'un article = somme des intensités de ses signaux + bonus si repris par plusieurs médias
    score = sg.groupby("article_id")["intensite"].sum().rename("score").reset_index()
    top = score.merge(df, left_on="article_id", right_on="id")
    top["score"] = (top["score"] + 0.2 * top["reprises"]).round(2)
    top = top.sort_values("score", ascending=False).head(15)
    st.dataframe(
        top[["date_pub", "source", "titre", "score", "reprises", "url"]],
        column_config={
            "date_pub": st.column_config.DatetimeColumn("Date", format="DD/MM HH:mm"),
            "url": st.column_config.LinkColumn("Lien", display_text="ouvrir"),
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=4),
            "reprises": "Reprises",
        },
        hide_index=True, width="stretch", height=420,
    )

# ------------------------------------------------------------
# Détail d'un article
# ------------------------------------------------------------
st.subheader("Détail d'un article")
choix = st.selectbox("Choisir un article", df.sort_values("date_pub", ascending=False)["titre"])
if choix:
    a = df[df["titre"] == choix].iloc[0]
    st.markdown(f"**{a['titre']}**  \n{a['source']} · {a['date_pub']:%d/%m/%Y %H:%M} · [lien]({a['url']})")
    st.write(a["resume"] or "_pas de résumé_")
    d1, d2, d3 = st.columns(3)
    d1.write("**Villes** : " + (", ".join(vi[vi.article_id == a.id]["ville"]) or "-"))
    d2.write("**Thèmes** : " + (", ".join(th[th.article_id == a.id]["theme"]) or "-"))
    d3.write("**Signaux** : " + (", ".join(sg[sg.article_id == a.id]["type_lisible"]) or "-"))
