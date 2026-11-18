# TP VéloToulouse - Plateforme de données quasi temps réel avec Microsoft Fabric

## Présentation

Ce projet répond au TP **« Building a unified data platform for real-time event analysis »**. Il vise à construire une chaîne de collecte, de traitement, de stockage et de visualisation de données fréquemment actualisées. Notre groupe utilise **Microsoft Fabric** et les données ouvertes de disponibilité des stations **VéloToulouse**.

**État du projet au 16 novembre 2026 :** la **partie 1 (ingestion)** a été validée par Karl sur plusieurs cycles ; la **partie 2 (traitement/stockage)** a été développée par Taha dans Fabric, avec deux tables exploitables ; la **partie 3 (Power BI)** est réalisée, publiée dans Fabric et testée sur les données déjà disponibles. 

## Architecture

```text
API Toulouse Métropole (VéloToulouse)
              |
              | Requêtes HTTP GET périodiques
              v
Python : ingestion_velotoulouse.py (Karl, exécuté sur son PC)
  - Pagination de 100 enregistrements
  - Lecture du JSON embarqué
  - Déduplication par station_id
  - Extraction vélos mécaniques / électriques
  - Horodatage et journalisation
              |
              | Azure Event Hubs SDK (AMQP over WebSockets)
              v
Microsoft Fabric — Eventstream ES_VeloToulouse
  Source : SRC_VeloToulouse_API
  Flux   : ES_VeloToulouse-stream
              |
              v
Lakehouse LH_VeloToulouse — station_raw (données amont)
              |
              v
Notebook Fabric : NB_VeloToulouse_Transform (Taha)
  - Nettoyage et préparation
  - Mise à jour de station_latest et station_history
              |
              v
Lakehouse LH_VeloToulouse
  - station_latest : dernier état par station
  - station_history : observations historiques
              |
              | SQL Analytics Endpoint / DirectQuery
              v
Power BI — VeloToulouse_Dashboard (partie 3)
  - KPI, graphiques et segments interactifs
  - Actualisation automatique de la page : 5 minutes
```

> L'API est interrogée toutes les **60 secondes** environ (intervalle entre les débuts de cycle, hors dépassement de durée). Il s'agit de **quasi-temps réel par polling**, et non d'un flux natif poussé par l'API. Le programme doit rester lancé pour continuer la collecte.

## Source de données

- **Portail :** [Toulouse Métropole Open Data](https://data.toulouse-metropole.fr/explore/dataset/velotoulouse-disponibilite-temps-reel/api/)

- **API Opendatasoft v2.1 :** `https://data.toulouse-metropole.fr/api/explore/v2.1/catalog/datasets/velotoulouse-disponibilite-temps-reel/records`

- **Méthode :** `GET` avec paramètres `limit=100` et `offset` pour la pagination.

- **Contenu :** nombre de vélos et de places disponibles, types de vélos, état de location et retour, horodatages et identifiants de stations.

Le nombre d'enregistrements API est supérieur au nombre de stations distinctes : plusieurs lignes peuvent correspondre à la même station. La transformation regroupe les lignes par `station_id` et conserve celle dont `last_reported` est le plus récent.

## Organisation du projet

```text
TP-VeloToulouse/
├── .env                       # Secret local, jamais versionné
├── .gitignore
├── README.md
├── requirements.txt
├── data/                      # Fichiers de travail éventuels
├── logs/
│   └── ingestion.log          # Journal généré à l'exécution
├── scripts/
│   ├── ingestion_velotoulouse.py
│   └── test_fabric.py
└── powerbi/
    └── VeloToulouse_Dashboard.pbix  # Rapport Power BI de la partie 3
```

## Prérequis

- Windows / PowerShell (ou un terminal équivalent)

- Python 3.12 (version utilisée pendant les tests)

- Accès à Microsoft Fabric et à un workspace disposant d'une capacité compatible

- Eventstream Fabric avec une source **Custom endpoint** configurée

- Accès Internet à l'API Toulouse Métropole

Dépendances du fichier `requirements.txt` :

```text
requests
azure-eventhub
python-dotenv
```

## Installation

Depuis PowerShell :

```powershell
cd "D:\TP-VeloToulouse"
python -m pip install -r requirements.txt
```

### Configuration des secrets

Créer le fichier `.env` à la racine du projet :

```dotenv
FABRIC_EVENTHUB_CONNECTION_STRING="<CHAINE_DE_CONNEXION_FABRIC>"
```

Récupérer la chaîne dans **Fabric → ES_VeloToulouse → source Custom endpoint → Details → SAS Key Authentication → Connection string-primary key**. Ne jamais publier cette valeur dans un dépôt, un rapport ou une capture d'écran. Vérifier que `.gitignore` contient au minimum :

```gitignore
.env
.venv/
__pycache__/
*.pyc
logs/
```

Si une clé est divulguée, la régénérer dans Fabric.

## Exécution

### Vérifier la connexion Fabric

```powershell
python scripts\test_fabric.py
```

Ce test envoie un événement synthétique ; il ne représente pas une station réelle.

### Lancer la collecte périodique

```powershell
python scripts\ingestion_velotoulouse.py
```

Paramètres principaux dans le script :

| Paramètre | Valeur | Rôle |
|---|---:|---|
| `INTERVAL` | `60` | Période cible entre débuts de collecte, en secondes |
| `PAGE_SIZE` | `100` | Taille des pages API |
| `MAX_STATIONS` | `0` | `0` = toutes les stations distinctes ; valeur positive = limitation de test |

Arrêter avec **Ctrl+C**. Pour lire les derniers journaux :

```powershell
Get-Content logs\ingestion.log -Tail 20
```

Pour voir uniquement les envois réussis :

```powershell
Select-String -Path logs\ingestion.log -Pattern "SUCCES"
```

## Structure des événements envoyés

Chaque événement représente l'état d'une station au moment d'une collecte.

| Champ | Description |
|---|---|
| `source` | Valeur `VeloToulouse` |
| `station_id` | Identifiant de station (chaîne) |
| `num_bikes_available` | Vélos disponibles |
| `num_docks_available` | Places libres |
| `num_bikes_disabled` | Vélos indisponibles |
| `mechanical_bikes` | Vélos mécaniques disponibles |
| `electrical_bikes` | Vélos électriques disponibles |
| `is_renting` | Location possible (booléen ou null) |
| `is_returning` | Retour possible (booléen ou null) |
| `last_reported` | Horodatage de dernière déclaration fourni par la source (Unix) |
| `collected_at` | Horodatage UTC de la collecte par Python (ISO 8601) |

Exemple **illustratif** (non extrait d'une observation précise) :

```json
{
  "source": "VeloToulouse",
  "station_id": "13",
  "num_bikes_available": 10,
  "num_docks_available": 5,
  "num_bikes_disabled": 0,
  "mechanical_bikes": 5,
  "electrical_bikes": 5,
  "is_renting": true,
  "is_returning": true,
  "last_reported": 1793964574,
  "collected_at": "2026-11-06T10:33:37+00:00"
}
```

## Validation réalisée — 6 novembre 2026

Des tests ont confirmé la récupération, la transformation et l'envoi vers Fabric :

| Cycle observé | Enregistrements API | Stations distinctes | Envoi Fabric |
|---|---:|---:|---|
| 10:33 | 3 368 | 466 | 466 événements, succès |
| 10:34 | 3 348 | 466 | 466 événements, succès |
| 10:35 | 3 360 | 466 | 466 événements, succès |

Une nouvelle collecte était en cours à 10:36. Les captures de **Data preview** dans Eventstream ont également montré des stations réelles et leurs valeurs (`num_bikes_available`, `num_docks_available`, `mechanical_bikes`, `electrical_bikes`, etc.).

**Attention :** « événements envoyés » signifie que le client producteur a confirmé l'envoi au point d'entrée Fabric ; cela ne prouve pas encore la persistance dans une base historique.

## Vérification dans Fabric

1. Ouvrir le workspace du groupe `TP-VeloToulouse`.

2. Ouvrir l'Eventstream `ES_VeloToulouse`.

3. Sélectionner `ES_VeloToulouse-stream`.

4. Dans **Data preview**, cliquer sur **Refresh** pendant l'exécution du script.

5. Vérifier la présence d'identifiants réels de stations et des champs de disponibilité.

Des événements de test antérieurs (par exemple `TEST001` avec d'autres noms de champs) peuvent encore apparaître dans l'aperçu. Les filtrer ou les exclure lors de la mise en place du stockage et des analyses.

## Gestion des erreurs et limites

- Requêtes HTTP avec délai maximal et nouvelles tentatives pour certains codes d'erreur (`429`, `5xx`).

- Refus des réponses JSON sans liste `results`, sans `total_count` valide ou des pages anormalement vides.

- Traitement des doublons par station et conservation de l'enregistrement le plus récent selon `last_reported`.

- Envoi par lots compatibles avec la taille maximale autorisée par Event Hubs.

- Journalisation dans le terminal et `logs/ingestion.log`.

- En cas d'erreur pendant un cycle, le script la journalise puis retente au cycle suivant.

**Limites connues :**

- La pagination d'une API actualisée en continu n'offre pas nécessairement un instantané atomique ; les données peuvent évoluer entre les pages.

- Le script dépend de l'ordinateur sur lequel il s'exécute ; il n'est pas encore hébergé comme service permanent.

- L'intervalle de 60 secondes doit être adapté si les limites de l'API ou de la capacité Fabric l'exigent.

- Les événements envoyés à chaque cycle représentent des observations successives : il est normal de retrouver la même station à différents `collected_at` dans l'historique.

- Le stockage historique et la visualisation sont désormais développés ; leur mise à jour automatique de bout en bout doit être revalidée après remise en service et correction du traitement planifié.

## Répartition du travail (3 personnes)

| Partie | Responsabilité | Livrable | État au 16/11/2026 |
|---|---|---|---|
| 1 — Ingestion (Karl) | API, Python, nettoyage, déduplication, Eventstream, logs | Événements transmis dans Fabric | **Validé sur plusieurs cycles**  |
| 2 — Stockage / traitement (Taha) | Notebook Fabric, préparation et historisation dans `LH_VeloToulouse` | Tables `station_latest` et `station_history` | **Développé et données consultables**  |
| 3 — Visualisation (Power BI) | KPI, graphiques, mesures DAX, filtres, publication et rafraîchissement | `powerbi/VeloToulouse_Dashboard.pbix` et rapport Fabric | **Réalisé et publié**  |

### Passage de relais initial à la partie 2

> Les indications ci-dessous correspondent au plan envisagé lors de la partie 1. La réalisation communiquée par Taha utilise un notebook Fabric et un Lakehouse, et non la destination Eventhouse proposée ici. Elles sont conservées comme trace du passage de relais initial.

- Utiliser le flux Fabric **`ES_VeloToulouse-stream`** comme source.

- Ajouter une destination **Eventhouse / KQL Database** et créer une table adaptée aux champs ci-dessus.

- Préserver `station_id` **et** `collected_at` pour analyser l'évolution dans le temps ; ne pas écraser toutes les observations d'une station.

- Exclure les événements de test (`TEST001`) ou les traiter séparément.

- Vérifier les types des colonnes, notamment `station_id`, booléens, entiers et dates.

- Vérifier le nombre de lignes ingérées et la latence entre `collected_at` et l'arrivée en base.

### Passage de relais initial à la partie 3

Idées de métriques Power BI : vélos disponibles par station, répartition mécaniques/électriques, stations vides ou saturées, évolution des disponibilités par heure et taux d'occupation approximatif. Les séries historiques nécessitent d'abord la mise en place de la partie 2.

## Partie 2 — Traitement et stockage des données avec Python (Taha)

### Objectif et environnement

Cette partie transforme les événements bruts stockés dans le Lakehouse en données nettoyées et exploitables par Power BI. Le traitement est réalisé dans le notebook Fabric **`NB_VeloToulouse_Transform`**, avec **Python, pandas, deltalake et PyArrow**, sans transformations PySpark.

Le pipeline principal utilise trois tables Delta dans **`LH_VeloToulouse`** :

| Table | Rôle |
|---|---|
| `dbo.station_raw` | Données brutes reçues depuis Eventstream |
| `dbo.station_history` | Historique nettoyé des observations successives |
| `dbo.station_latest` | Dernière observation disponible pour chaque station |

### Lecture des données et authentification

Le notebook lit `station_raw` depuis OneLake avec `DeltaTable(...).to_pandas()`. Les données sont chargées dans un DataFrame pandas pour appliquer les règles de nettoyage.

L'accès au stockage utilise explicitement un jeton fourni par Fabric :

```python
from deltalake import DeltaTable

storage_options = {
    "bearer_token": notebookutils.credentials.getToken("storage"),
    "use_fabric_endpoint": "true",
}

df = DeltaTable(
    table_path,
    storage_options=storage_options,
).to_pandas()
```

La variable `table_path` désigne le chemin OneLake de `dbo.station_raw`. Les chemins de `station_history` et `station_latest` sont construits dans le même Lakehouse.

Cette authentification explicite a résolu les erreurs de lecture liées à la recherche d'une identité managée via le service de métadonnées. Elle est également utilisée pour lire et écrire les tables transformées.

### Nettoyage et normalisation

Le DataFrame brut est copié dans `clean`, puis les règles suivantes sont appliquées :

| Élément | Transformation ou contrôle |
|---|---|
| `station_id` | Conversion en chaîne et suppression des espaces au début et à la fin |
| Identifiant absent ou vide | Exclusion du relevé |
| Station de test `TEST001` | Exclusion du relevé |
| `collected_at` | Conversion du texte ISO 8601 en date UTC ; exclusion si la conversion échoue |
| `last_reported` | Conversion de l'horodatage Unix en secondes vers une nouvelle colonne `last_reported_at` en UTC |
| `last_reported` nul, invalide ou non positif | Date `last_reported_at` manquante ; ce seul critère n'exclut pas le relevé |
| `num_bikes_available` | Conservation uniquement si la valeur est supérieure ou égale à zéro |
| `num_docks_available` | Conservation uniquement si la valeur est supérieure ou égale à zéro |
| Doublons du lot | Conservation d'une seule ligne par couple `station_id` + `collected_at` |

Le champ `last_reported` d'origine est conservé. Les deux dates n'ont pas le même sens : **`collected_at` indique quand notre script a collecté la donnée**, tandis que **`last_reported_at` indique la dernière déclaration de la station selon la source**.

Les valeurs de disponibilité ne sont pas modifiées pour créer artificiellement des changements. Une station peut donc conserver le même nombre de vélos pendant plusieurs collectes.

### Historisation avec un MERGE Delta Lake

Après nettoyage, les données sont converties en table PyArrow. Les colonnes de dates sont converties en précision microseconde UTC avant l'écriture Delta.

Lors de la première exécution, `station_history` est créée si elle n'existe pas. Lors des exécutions suivantes, un **MERGE** compare les données entrantes aux observations déjà stockées avec la clé :

```text
station_id + collected_at
```

- Si ce couple n'existe pas encore, le nouveau relevé est inséré.
- Si ce couple existe déjà, aucune nouvelle ligne n'est ajoutée pour ce relevé.
- Le MERGE utilisé ne met pas à jour les lignes déjà présentes.

Cette règle rend l'alimentation de l'historique **idempotente** : rejouer les mêmes données n'augmente pas le nombre de lignes.

En revanche, la même station observée à deux dates de collecte différentes produit bien deux lignes historiques, même si sa disponibilité ne change pas. Il s'agit de deux observations successives, utiles pour suivre son état dans le temps.

### Construction du dernier état par station

Le notebook relit l'historique nettoyé, trie les observations de la plus récente à la plus ancienne selon `collected_at`, puis conserve une seule ligne par station :

```python
history_df = DeltaTable(
    history_path,
    storage_options=storage_options,
).to_pandas()

latest = (
    history_df
    .sort_values("collected_at", ascending=False)
    .drop_duplicates(subset="station_id", keep="first")
)
```

Le résultat remplace le contenu de **`station_latest`**. Lors des tests, cette table contenait **466 lignes pour 466 stations distinctes**.

Power BI peut ainsi utiliser `station_latest` pour les indicateurs actuels et `station_history` pour les évolutions temporelles. Le dernier état disponible peut être ancien si la collecte est arrêtée ; il ne garantit pas à lui seul la fraîcheur des données.

### Automatisation du notebook principal

Le notebook **`NB_VeloToulouse_Transform`** est enregistré et planifié dans Fabric **toutes les 5 minutes**.

À chaque exécution, il réalise la lecture des données brutes, le nettoyage, le MERGE de l'historique et la reconstruction du dernier état par station.

La planification du traitement principal a été testée avec succès après correction des accès au stockage. L'avancement de `collected_at` dans `station_latest` a été vérifié pendant que l'ingestion fonctionnait.

Cette planification est distincte de celle du notebook **`_IaC_Demo`**, décrite plus loin.

### Validation réalisée

| Contrôle | Résultat observé |
|---|---|
| Lecture et nettoyage d'un jeu de données de test | 35 013 relevés bruts et 35 013 relevés conservés |
| Nombre de stations distinctes | 466 |
| Réexécution d'un lot déjà historisé | 0 nouvelle ligne ajoutée lors de la seconde exécution |
| Unicité du dernier état | Une seule ligne par `station_id` dans `station_latest` |
| Exécution planifiée du notebook principal | Exécution réussie |
| Actualisation des données transformées | Progression de `collected_at` constatée lorsque l'ingestion était active |

Les volumes indiqués correspondent à des tests et évoluent avec les nouvelles collectes. Le fait de conserver toutes les lignes du jeu de test signifie qu'aucune ne contrevenait aux règles appliquées ; cela ne constitue pas une garantie de qualité exhaustive.

### Limites du traitement actuel

- La lecture de `station_raw` charge actuellement l'ensemble de la table en mémoire pandas. Le MERGE évite les réinsertions, mais la lecture et le nettoyage ne sont pas encore incrémentaux.
- Le dernier état est reconstruit en relisant l'historique complet. Une stratégie de lecture incrémentale pourra être envisagée si le volume augmente.
- Les contrôles appliqués portent sur les identifiants, les dates de collecte et les disponibilités de vélos et de places. Ils ne couvrent pas toutes les incohérences possibles entre les compteurs.
- La fraîcheur des tables dépend de la collecte amont et du succès des exécutions planifiées.

## Partie 3 — Visualisation Power BI (réalisée)

### Objectif et livrable

La visualisation exploite les données préparées dans Microsoft Fabric pour suivre l'état du réseau VéloToulouse et analyser ses évolutions. Le rapport est disponible dans le workspace **`TP-VeloToulouse`** sous le nom **`VeloToulouse_Dashboard`**. Son fichier source versionnable est **`powerbi/VeloToulouse_Dashboard.pbix`**.

### Connexion et modèle de données

- **Source** : point de terminaison SQL Analytics du Lakehouse `LH_VeloToulouse`.
- **Mode de stockage** : **DirectQuery**. Power BI interroge les tables du Lakehouse lors de l'exécution des requêtes des visuels ; aucune copie Import permanente n'est utilisée dans le modèle du rapport.
- **Tables utilisées** : `station_latest` pour l'état courant et `station_history` pour les relevés successifs. `station_raw` n'est pas utilisée par les visualisations.
- **Relation** : `station_latest[station_id]` (côté **1**) → `station_history[station_id]` (côté `*`), relation active et filtrage croisé **simple**. Ainsi, sélectionner une station dans la table des états récents filtre également son historique.
- **Modèle sémantique publié** : `VeloToulouse_Dashboard`, créé lors de la publication du fichier Power BI Desktop.

Le choix de DirectQuery est adapté à la consultation de données régulièrement mises à jour : il ne dispense toutefois pas de relancer les requêtes des visuels, ni d'assurer l'ingestion et le traitement en amont.

### Indicateurs (mesures DAX)

| Indicateur | Définition | Table |
|---|---|---|
| Total vélos disponibles | Somme de `num_bikes_available` | `station_latest` |
| Total places disponibles | Somme de `num_docks_available` | `station_latest` |
| Nombre de stations distinctes | Nombre de `station_id` distincts | `station_latest` |
| Taux de remplissage indicatif | Vélos disponibles / (vélos disponibles + places libres) | Mesures basées sur `station_latest` |
| Total vélos électriques | Somme de `electrical_bikes` | `station_latest` |
| Total vélos mécaniques | Somme de `mechanical_bikes` | `station_latest` |
| Stations par relevé | Nombre de stations distinctes pour un horodatage | `station_history` |
| Dernier relevé actuel / historique | Date maximale de `collected_at` pour chaque table | Les deux tables |

Quelques exemples de mesures :

```dax
Total vélos disponibles =
SUM('station_latest'[num_bikes_available])

Total places disponibles =
SUM('station_latest'[num_docks_available])

Taux de remplissage =
DIVIDE(
    [Total vélos disponibles],
    [Total vélos disponibles] + [Total places disponibles]
)
```

Le taux de remplissage est **indicatif** : il correspond aux vélos **disponibles** rapportés aux vélos disponibles et aux places libres ; il ne mesure pas nécessairement l'occupation physique réelle, notamment si des vélos indisponibles occupent des emplacements.

### Contrôle qualité de l'historique

Les relevés historiques représentent des états successifs du réseau. Il ne faut donc **pas additionner les vélos de tous les horodatages** pour obtenir la disponibilité à un instant donné.


La mesure DAX utilisée pour la courbe est de la forme :

```dax
Vélos historiques filtrés =
VAR StationsDuReleve =
    CALCULATE(
        DISTINCTCOUNT('station_history'[station_id]),
        REMOVEFILTERS('station_latest')
    )
VAR VelosDisponibles =
    SUM('station_history'[num_bikes_available])
RETURN
    IF(
        HASONEVALUE('station_history'[collected_at])
            && StationsDuReleve = 466,
        VelosDisponibles,
        BLANK()
    )
```

**Pourquoi cette logique ?** Le contrôle du nombre de stations doit être réalisé sur l'ensemble du réseau, même lorsqu'un segment filtre une station particulière. Le total des vélos, lui, doit rester filtré sur la station sélectionnée. `HASONEVALUE` évite d'afficher un total artificiel agrégeant plusieurs relevés.

**Limite actuelle :** la valeur **466** est codée en dur parce qu'elle correspond au nombre observé pendant les tests. Si le réseau gagne ou perd des stations, le seuil de complétude devra être revu. Une approche plus robuste consisterait à calculer le nombre de stations attendu par période.

### Visuels et interactions

La page principale du rapport présente :

- **Quatre cartes KPI** : vélos disponibles, places libres, nombre de stations et taux de remplissage indicatif.
- **Un graphique en anneau** : répartition des vélos mécaniques et électriques disponibles.
- **Un graphique en barres** : représentant l'approvisionnement des stations.
- **Une courbe historique** : évolution des vélos disponibles par relevé complet.
- **Deux segments interactifs** : sélection d'une station (`station_id`) et filtrage de la période (`collected_at`).

La relation entre les tables permet au filtre station de modifier aussi bien les indicateurs actuels que la courbe historique. Les visuels et l'interactivité ont été testés dans **Power BI Desktop** puis après **publication dans Fabric**.

La courbe historique peut relier visuellement des points éloignés lorsque des périodes n'ont pas de relevés exploitables : ces segments ne constituent **pas** des mesures intermédiaires et ne doivent pas être interprétés comme une évolution continue observée.

### Actualisation et fraîcheur

- **Actualisation automatique de page** : configurée à **5 minutes** dans Power BI Desktop, puis vérifiée dans le rapport publié ; elle est applicable lorsque la page est ouverte/active et dans les limites imposées par la capacité Fabric.
- **Mode DirectQuery** : les requêtes peuvent récupérer les nouvelles lignes visibles sur le point de terminaison SQL, mais l'actualisation de page ne déclenche pas les traitements de Karl et Taha.
- **Surveillance de fraîcheur** : des mesures `MAX(collected_at)` sur `station_latest` et `station_history` donnent l'heure du dernier relevé disponible. Les horodatages issus du script sont en UTC ; vérifier la présentation du fuseau horaire dans le rapport.

### Vérification et démonstration

1. Ouvrir `TP-VeloToulouse` dans Microsoft Fabric et lancer le rapport `VeloToulouse_Dashboard`.
2. Vérifier que les cartes et les graphiques se chargent depuis le Lakehouse.
3. Dans le segment station, sélectionner la station **151** : lors du test, les cartes indiquaient **21 vélos disponibles**, **1 place libre** et **1 station** ; la courbe historique se filtrait également.
4. Effacer le filtre station et sélectionner une période dans le segment de dates pour observer l'évolution historique.

## Référence du TP

[SUPINFO — 5CLOU Exam : 01-my-data-platform](https://github.com/SUPINFO-Organization/5CLOU-Exam/tree/main/01-my-data-platform)

Le sujet demande une plateforme d'ingestion, de traitement et de visualisation de données mises à jour fréquemment. Le groupe a choisi **Microsoft Fabric Eventstream + Python** pour l'ingestion, puis **notebook Fabric + Lakehouse** pour le traitement et **Power BI** pour la visualisation. Cette architecture est l'implémentation choisie par le groupe ; elle n'est pas identique au parcours Azure Data Factory / Synapse mentionné dans le barème du sujet.


---

## Infrastructure as Code — Terraform, Docker, GitHub Actions et Power BI

Cette partie complète le TP avec une **démonstration Infrastructure as Code (IaC)**. L'objectif est de reproduire la chaîne VéloToulouse dans des ressources Microsoft Fabric séparées, d'automatiser une ingestion et de démontrer que le déploiement aboutit à des données consultables dans Power BI.

**Périmètre :** les ressources principales du groupe (ingestion de Karl, transformations de Taha et rapport Power BI principal) restent **inchangées**. Terraform crée et administre uniquement des **copies de démonstration** suffixées `_IaC_Demo`.

### Architecture de démonstration

~~~text
API Open Data Toulouse Métropole (VéloToulouse)
                 |
                 | Python : test_ingestion_once.py
                 | GitHub Actions : exécution manuelle ou quotidienne
                 v
Eventstream Fabric : ES_VeloToulouse_IaC_Demo
                 |
                 v
Lakehouse Fabric : LH_VeloToulouse_IaC_Demo
  dbo.station_raw
                 |
                 | Notebook NB_VeloToulouse_Transform_IaC_Demo
                 | (exécution planifiée séparément dans Fabric)
                 v
  dbo.station_history  +  dbo.station_latest
                 |
                 | SQL Analytics Endpoint / DirectQuery
                 v
Modèle sémantique : VeloToulouse_Dashboard_IaC_Demo_Model
                 |
                 v
Rapport Power BI : VeloToulouse_Dashboard_IaC_Demo
~~~

Il s'agit d'une architecture **quasi temps réel du point de vue des données source**, mais la copie de démonstration est **actualisée périodiquement** : le déclencheur GitHub Actions et celui du notebook n'assurent pas un flux continu de bout en bout.

### Ce qui est géré par Terraform

Le provider `microsoft/fabric` (version utilisée pendant le projet : `1.13.0`) déploie **cinq ressources Fabric** :

| Type Terraform | Ressource créée | Usage |
|---|---|---|
| `fabric_lakehouse` | `LH_VeloToulouse_IaC_Demo` | Stockage des données brutes et transformées |
| `fabric_eventstream` | `ES_VeloToulouse_IaC_Demo` | Réception des événements Python et alimentation de `dbo.station_raw` |
| `fabric_notebook` | `NB_VeloToulouse_Transform_IaC_Demo` | Transformation, historique et dernier état des stations |
| `fabric_semantic_model` | `VeloToulouse_Dashboard_IaC_Demo_Model` | Modèle TMDL en DirectQuery vers le Lakehouse Demo |
| `fabric_report` | `VeloToulouse_Dashboard_IaC_Demo` | Rapport PBIR connecté au nouveau modèle sémantique |

Le workspace `TP-VeloToulouse` et les cinq ressources **principales** existantes sont référencés au moyen de **data sources Terraform en lecture seule** dans `main.tf` et `inventory.tf`. Terraform ne les remplace pas et ne les détruit pas.

Les définitions exportées de Fabric sont rendues réutilisables grâce à des modèles `.tmpl` et des tokens Terraform : ID du workspace et du Lakehouse pour le notebook et l'Eventstream, nom du Lakehouse pour les partitions TMDL, ID du modèle sémantique pour le rapport PBIR.

### Structure des fichiers IaC

~~~text
terraform/
├── Dockerfile                    # Image Azure CLI + Terraform
├── Dockerfile.ingestion-test     # Environnement Python de test
├── docker-compose.yaml           # Services iac et ingestion-test
├── providers.tf
├── main.tf                       # Workspace existant
├── inventory.tf                  # Inventaire en lecture seule
├── demo_lakehouse.tf
├── demo_eventstream.tf
├── demo_notebook.tf
├── demo_semanticmodel.tf
├── demo_report.tf
├── test_ingestion_once.py
├── export_powerbi.py
├── prepare_powerbi.py
├── definitions/
│   ├── ES_VeloToulouse/          # Définition Eventstream
│   ├── NB_VeloToulouse_Transform/# Notebook avec tokens
│   └── PowerBI/
│       ├── SemanticModel/        # TMDL, mesures et partitions
│       └── Report/               # PBIR, pages, visuels, thème
└── .secrets/                     # Local : non versionné

.github/workflows/
└── ingestion_demo.yml            # Exécution GitHub Actions
~~~

Le code de l'ingestion et celui des transformations restent basés sur les composants développés pour le pipeline principal ; le but n'est pas de réécrire les travaux de Karl ou de Taha.

### Exécuter Terraform dans Docker

**Prérequis :** Docker Desktop, accès au workspace Microsoft Fabric et autorisations de création des ressources concernées. La connexion Azure CLI est conservée dans un volume Docker ; le code et l'état Terraform restent dans le dossier local `terraform/`.

Depuis **la racine du dépôt**, dans PowerShell :

~~~powershell
# Construire les images
docker compose -f ./terraform/docker-compose.yaml build

# Se connecter à Microsoft (si nécessaire)
docker compose -f ./terraform/docker-compose.yaml run --rm iac az login --use-device-code --allow-no-subscriptions

# Préparer et contrôler l'infrastructure
docker compose -f ./terraform/docker-compose.yaml run --rm iac terraform init
docker compose -f ./terraform/docker-compose.yaml run --rm iac terraform fmt -check
docker compose -f ./terraform/docker-compose.yaml run --rm iac terraform validate
docker compose -f ./terraform/docker-compose.yaml run --rm iac terraform plan
~~~

Avant un premier déploiement, vérifier les ressources affichées dans le plan, puis seulement :

~~~powershell
docker compose -f ./terraform/docker-compose.yaml run --rm iac terraform apply
~~~

**Ne pas exécuter `terraform apply` depuis un autre clone sans récupérer le même état Terraform.** Le fichier `terraform.tfstate` est actuellement **local** et exclu de Git : un nouveau poste ne sait pas automatiquement que les cinq ressources Demo existent déjà.

### Ingestion et automatisation GitHub Actions

Le script `terraform/test_ingestion_once.py` reprend le traitement de l'API et l'envoi via Azure Event Hubs SDK, mais réalise **une seule collecte**, contrairement au script d'ingestion principal exécuté en boucle.

Le service Docker `ingestion-test` lit sa chaîne de connexion depuis `terraform/.secrets/eventstream-demo.env` (variable `EVENTHUB_CONNECTION_STRING`). Ce fichier est **local et ignoré par Git**.

~~~powershell
# Test complet : toutes les stations, sans boucle permanente
docker compose -f ./terraform/docker-compose.yaml run --rm -e INGESTION_MAX_STATIONS=0 ingestion-test
~~~

Le workflow `.github/workflows/ingestion_demo.yml` fournit :

- Un lancement manuel depuis l'onglet **Actions** de GitHub.
- Un déclenchement automatique quotidien à **07 h 17 UTC** (08 h 17 en France en heure d'hiver, 09 h 17 en heure d'été).
- Une installation temporaire des dépendances Python et une collecte de toutes les stations.
- Une étape de diagnostic de la réponse de l'API, utile pendant les tests.
- L'injection sécurisée du secret GitHub Actions `FABRIC_EVENTHUB_CONNECTION_STRING_DEMO`.

Une tâche planifiée GitHub Actions peut démarrer avec du retard ou échouer si l'API externe est indisponible. Des réponses API contenant temporairement zéro résultat ont effectivement été rencontrées pendant le projet.

### Transformation, historique et Power BI

Le notebook Demo traite les données du Lakehouse Demo, puis :

- alimente `station_history` par **MERGE Delta Lake** sur la clé `(station_id, collected_at)`, afin de limiter les doublons lors des réexécutions ;
- reconstruit `station_latest` avec l'observation la plus récente de chaque station.

Une **planification quotidienne du notebook a été configurée manuellement dans Fabric**, autour de 10 h 40 (heure de Paris), avec une fin initialement prévue le **20 novembre 2026**. **Cette planification n'est pas gérée par les fichiers Terraform** et devra être prolongée si l'environnement doit fonctionner durablement.

Le modèle sémantique Demo lit `station_latest` et `station_history` par **DirectQuery** via le SQL Analytics Endpoint du Lakehouse Demo. Le rapport PBIR est relié à ce **nouveau modèle**. Les cartes KPI, graphiques, filtres et mesures DAX sont issus du rapport Power BI du groupe.

**Limite de l'orchestration :** GitHub Actions et le planificateur du notebook Fabric fonctionnent séparément. Une exécution du notebook n'est pas conditionnée au succès de l'ingestion du jour.

### Validation effectuée le 18 novembre 2026

| Contrôle | Résultat observé |
|---|---|
| Validation de la configuration Terraform | `terraform validate` : configuration valide |
| Plan Terraform avant ajout du modèle et du rapport | `2 to add, 0 to change, 0 to destroy` |
| GitHub Actions, ingestion complète réussie | 3 368 enregistrements API, 466 stations distinctes, 466 événements envoyés |
| `dbo.station_raw` | 937 lignes après les tests d'ingestion |
| `dbo.station_history` | 937 lignes après transformation |
| `dbo.station_latest` | 466 stations |
| Notebook de transformation | Exécution manuelle et exécution planifiée validées |
| Rapport Power BI Demo | Visuels et quatre KPI affichés avec des données du Lakehouse Demo |

Ces chiffres correspondent **aux relevés consultés pendant les tests** et évolueront après de nouvelles collectes. Le chargement du rapport prouve le fonctionnement de cette chaîne à la date du test ; il ne garantit pas l'absence d'incidents futurs. Un nouveau `terraform plan` permet de vérifier qu'aucune dérive n'est détectée après déploiement.

### Sécurité et limites

- **Ne jamais versionner** les fichiers `.env`, `.secrets/`, les exports bruts de connexion ou `*.tfstate` / `*.tfstate.*`.
- Le secret Eventstream n'apparaît ni dans le code du workflow ni dans le README ; il est conservé localement ou dans **GitHub Actions Secrets**.
- Les définitions PBIR/TMDL versionnées ne sont pas des fichiers de données historiques ; elles décrivent le rapport et le modèle.
- Le **state Terraform est local**, sans backend distant ni verrouillage multi-utilisateur : la reprise sur une autre machine nécessite une procédure explicite.
- La planification du notebook et les secrets GitHub sont configurés **hors Terraform** : un clonage du dépôt ne suffit pas à les recréer.
- Le pipeline **principal** n'est pas administré par cet état Terraform.
- Ne lancer `terraform destroy` qu'après analyse détaillée des conséquences sur les ressources Demo.

**Bilan :** cette partie démontre le provisionnement de cinq ressources Fabric par Terraform, une ingestion automatisable sur GitHub Actions et une exploitation de données réelles jusqu'à un rapport Power BI, sans modifier le fonctionnement du pipeline principal.
