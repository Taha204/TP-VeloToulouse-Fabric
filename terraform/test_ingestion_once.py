
import os
import sys
from pathlib import Path

from azure.eventhub import EventHubProducerClient, TransportType

# Accéder au code original de Karl
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Récupérer la connexion de l'Eventstream de démonstration
connection = os.getenv("EVENTHUB_CONNECTION_STRING")

if not connection:
    raise RuntimeError(
        "Connexion de demonstration absente."
    )

# Fournir à Karl le nom de variable attendu
os.environ["FABRIC_EVENTHUB_CONNECTION_STRING"] = connection

from scripts import ingestion_velotoulouse as ingestion


def main():
    print("Récupération des données VéloToulouse...")

    # Réessayer une collecte complète si l'API renvoie
    # temporairement un total_count incohérent.
    for attempt in range(1, 4):
        try:
            records = ingestion.fetch_stations()
            break

        except RuntimeError as exc:
            if (
                "L'API ne retourne aucun enregistrement" not in str(exc)
                or attempt == 3
            ):
                raise

            print(
                f"Réponse API incohérente. "
                f"Nouvelle tentative {attempt + 1}/3..."
            )
            time.sleep(3 * attempt)
    events = ingestion.transform_records(records)

    if not events:
        raise RuntimeError("Aucune station valide reçue.")

    print(f"Stations disponibles : {len(events)}")

    # 5 stations par défaut
    # 0 = toutes les stations
    limit = int(os.getenv("INGESTION_MAX_STATIONS", "5"))

    if limit < 0:
        raise ValueError("INGESTION_MAX_STATIONS doit être >= 0")

    test_events = events if limit == 0 else events[:limit]

    print(f"Envoi de {len(test_events)} stations de test...")

    with EventHubProducerClient.from_connection_string(
        conn_str=connection,
        transport_type=TransportType.AmqpOverWebsocket,
        retry_total=5,
        logging_enable=False,
    ) as producer:
        sent = ingestion.send_events(
            producer, test_events
        )

    print(f"SUCCÈS : {sent} événements envoyés.")
    print("Fin du test. Aucune boucle continue.")


if __name__ == "__main__":
    main()
