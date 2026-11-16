# TP VéloToulouse — Plateforme de données quasi temps réel avec Microsoft Fabric

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

## Infrastructure as Code — Terraform & Docker

Une infrastructure as code (IaC) a été mise en place avec
Terraform, Docker et Azure CLI pour administrer des ressources
Microsoft Fabric.

### Architecture IaC

Le dossier `terraform/` contient :

- `Dockerfile` : image avec Terraform et Azure CLI.
- `docker-compose.yaml` : configuration des conteneurs et volumes.
- `providers.tf` : provider Microsoft Fabric.
- `main.tf` : connexion au workspace existant.
- `inventory.tf` : inventaire des ressources Fabric.
- `demo_lakehouse.tf` : déploiement d'un Lakehouse de démonstration.

### Ressources Microsoft Fabric

Terraform consulte en lecture seule les ressources existantes :

- Workspace `TP-VeloToulouse`
- Eventstream `ES_VeloToulouse`
- Lakehouse `LH_VeloToulouse`
- Notebook `NB_VeloToulouse_Transform`
- Rapport Power BI `VeloToulouse_Dashboard`
- Modèle sémantique `VeloToulouse_Dashboard`

Un Lakehouse supplémentaire, `LH_VeloToulouse_IaC_Demo`,
a été réellement créé et est géré avec Terraform.

### Exécution

Toutes les commandes s'exécutent depuis la racine du dépôt.

```powershell
# Construire l'environnement Docker
docker compose -f ./terraform/docker-compose.yaml build

# Authentification Microsoft
docker compose -f ./terraform/docker-compose.yaml run --rm iac az login --use-device-code --allow-no-subscriptions

# Initialisation Terraform
docker compose -f ./terraform/docker-compose.yaml run --rm iac terraform init

# Validation
docker compose -f ./terraform/docker-compose.yaml run --rm iac terraform validate

# Prévisualisation
docker compose -f ./terraform/docker-compose.yaml run --rm iac terraform plan
```

### Résultats

Le déploiement du Lakehouse de démonstration a réussi :

`Apply complete! Resources: 1 added, 0 changed, 0 destroyed.`

Une nouvelle exécution de `terraform plan` a confirmé :

`No changes. Your infrastructure matches the configuration.`

Cela démontre le provisionnement automatisé et l'idempotence.

### Sécurité et limites

- Le fichier `terraform.tfstate` est conservé localement et exclu de Git.
- Les ressources du pipeline principal ne sont pas gérées par Terraform : elles sont uniquement consultées.
- Le Lakehouse de démonstration est la seule ressource actuellement provisionnée et gérée par Terraform.
- Un nouveau clone GitHub ne récupère pas le state local. Il ne faut pas lancer `terraform apply` depuis une autre machine sans reprendre l'état existant ou configurer un backend distant sécurisé.
- Ne jamais exécuter `terraform destroy` sans vérifier précisément les ressources concernées.
```
