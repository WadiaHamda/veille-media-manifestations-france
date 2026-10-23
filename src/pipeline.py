"""
pipeline.py - lance toutes les étapes dans l'ordre
python src/pipeline.py
"""
from db import creer_base
from collect import collecter
from dedup import nettoyer
from enrich import enrichir

if __name__ == "__main__":
    print("=== Etape 1 : base de données ===")
    creer_base()
    print("\n=== Etape 2 : collecte des articles ===")
    collecter()
    print("\n=== Etape 3 : doublons ===")
    nettoyer()
    print("\n=== Etape 3 bis : villes, thèmes, signaux ===")
    enrichir()
    print("\nC'est bon ! Lance le dashboard : streamlit run app/dashboard.py")
