
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

    records = ingestion.fetch_stations()
    events = ingestion.transform_records(records)

    if not events:
        raise RuntimeError("Aucune station valide reçue.")

    print(f"Stations disponibles : {len(events)}")

    # Un seul lot limité à 5 stations
    test_events = events[:5]

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
