-- ============================================
-- Projet : Veille média - Manifestations en France (octobre 2026)
-- Base de données SQLite
-- ============================================

PRAGMA foreign_keys = ON;

-- Les articles récupérés
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    titre           TEXT NOT NULL,
    url             TEXT NOT NULL,
    url_normalisee  TEXT UNIQUE,          -- url sans les ?utm etc
    source          TEXT,                 -- ex: Le Monde, France Info
    date_pub        TEXT,                 -- format AAAA-MM-JJ HH:MM
    resume          TEXT,
    hash_titre      TEXT,                 -- pour trouver les doublons exacts
    groupe_id       INTEGER,              -- articles quasi identiques (reprise AFP)
    est_doublon     INTEGER DEFAULT 0,    -- 1 = doublon, on le garde mais on l'ignore
    date_collecte   TEXT DEFAULT (datetime('now'))
);

-- Les villes (on remplit avec les grandes villes de France)
CREATE TABLE IF NOT EXISTS villes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT UNIQUE NOT NULL,
    region      TEXT,
    latitude    REAL,
    longitude   REAL
);

-- Les thèmes des manifestations
CREATE TABLE IF NOT EXISTS themes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle     TEXT UNIQUE NOT NULL,
    mots_cles   TEXT                      -- mots séparés par des virgules
);

-- Les signaux détectés dans un article
CREATE TABLE IF NOT EXISTS signal (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id  INTEGER NOT NULL,
    type        TEXT NOT NULL,            -- appel_mobilisation, syndicat, reaction_politique, violences
    intensite   REAL,                     -- entre 0 et 1
    description TEXT,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

-- Tables de liaison (un article peut parler de plusieurs villes / thèmes)
CREATE TABLE IF NOT EXISTS article_ville (
    article_id  INTEGER,
    ville_id    INTEGER,
    PRIMARY KEY (article_id, ville_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (ville_id)   REFERENCES villes(id)
);

CREATE TABLE IF NOT EXISTS article_theme (
    article_id  INTEGER,
    theme_id    INTEGER,
    score       INTEGER,                  -- nombre de mots clés trouvés
    PRIMARY KEY (article_id, theme_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (theme_id)   REFERENCES themes(id)
);

CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date_pub);
CREATE INDEX IF NOT EXISTS idx_signal_type ON signal(type);

-- ============================================
-- Données de référence : thèmes
-- ============================================
INSERT OR IGNORE INTO themes (libelle, mots_cles) VALUES
('Retraites',     'retraite,retraites,pension,âge légal,réforme des retraites'),
('Budget / Impôts','budget,impôt,impôts,taxe,fiscalité,austérité,loi de finances,PLF'),
('Salaires / Pouvoir d''achat','salaire,salaires,pouvoir d''achat,smic,inflation,prix,vie chère'),
('Agriculture',   'agriculteur,agriculteurs,paysan,FNSEA,Coordination rurale,tracteur,Mercosur'),
('Éducation',     'enseignant,enseignants,professeur,école,lycée,université,étudiant,étudiants'),
('Santé',         'hôpital,hôpitaux,soignant,soignants,infirmier,infirmières,médecin,urgences'),
('Logement',      'logement,loyer,loyers,expulsion,HLM,mal-logement'),
('Environnement', 'climat,écologie,écologistes,bassines,Extinction Rebellion,pesticide'),
('Transports',    'SNCF,RATP,cheminot,cheminots,train,transport,aérien,contrôleurs aériens'),
('Sécurité / Police','police,policiers,violences policières,maintien de l''ordre'),
('International', 'Palestine,Gaza,Israël,Ukraine,guerre,paix');

-- ============================================
-- Données de référence : villes principales
-- ============================================
INSERT OR IGNORE INTO villes (nom, region, latitude, longitude) VALUES
('Paris','Île-de-France',48.8566,2.3522),
('Marseille','Provence-Alpes-Côte d''Azur',43.2965,5.3698),
('Lyon','Auvergne-Rhône-Alpes',45.7640,4.8357),
('Toulouse','Occitanie',43.6047,1.4442),
('Nice','Provence-Alpes-Côte d''Azur',43.7102,7.2620),
('Nantes','Pays de la Loire',47.2184,-1.5536),
('Montpellier','Occitanie',43.6108,3.8767),
('Strasbourg','Grand Est',48.5734,7.7521),
('Bordeaux','Nouvelle-Aquitaine',44.8378,-0.5792),
('Lille','Hauts-de-France',50.6292,3.0573),
('Rennes','Bretagne',48.1173,-1.6778),
('Reims','Grand Est',49.2583,4.0317),
('Toulon','Provence-Alpes-Côte d''Azur',43.1242,5.9280),
('Saint-Étienne','Auvergne-Rhône-Alpes',45.4397,4.3872),
('Le Havre','Normandie',49.4944,0.1079),
('Grenoble','Auvergne-Rhône-Alpes',45.1885,5.7245),
('Dijon','Bourgogne-Franche-Comté',47.3220,5.0415),
('Angers','Pays de la Loire',47.4784,-0.5632),
('Nîmes','Occitanie',43.8367,4.3601),
('Clermont-Ferrand','Auvergne-Rhône-Alpes',45.7772,3.0870),
('Le Mans','Pays de la Loire',48.0061,0.1996),
('Brest','Bretagne',48.3904,-4.4861),
('Tours','Centre-Val de Loire',47.3941,0.6848),
('Amiens','Hauts-de-France',49.8941,2.2958),
('Limoges','Nouvelle-Aquitaine',45.8336,1.2611),
('Perpignan','Occitanie',42.6887,2.8948),
('Metz','Grand Est',49.1193,6.1757),
('Besançon','Bourgogne-Franche-Comté',47.2378,6.0241),
('Orléans','Centre-Val de Loire',47.9030,1.9093),
('Rouen','Normandie',49.4432,1.0999),
('Caen','Normandie',49.1829,-0.3707),
('Nancy','Grand Est',48.6921,6.1844),
('Mulhouse','Grand Est',47.7508,7.3359),
('Poitiers','Nouvelle-Aquitaine',46.5802,0.3404),
('Pau','Nouvelle-Aquitaine',43.2951,-0.3708),
('La Rochelle','Nouvelle-Aquitaine',46.1603,-1.1511),
('Bayonne','Nouvelle-Aquitaine',43.4929,-1.4748),
('Avignon','Provence-Alpes-Côte d''Azur',43.9493,4.8055),
('Ajaccio','Corse',41.9192,8.7386),
('Bastia','Corse',42.6973,9.4509),
('Saint-Denis','Île-de-France',48.9362,2.3574),
('Nanterre','Île-de-France',48.8924,2.2071);
