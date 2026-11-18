
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = BASE / ".secrets" / "powerbi-original"
DESTINATION = BASE / "definitions" / "PowerBI"

OLD_DATABASE = '"LH_VeloToulouse"'
NEW_DATABASE = '"{{ .LakehouseName }}"'


def prepare(folder, output_name):
    source = SOURCE / folder
    target = DESTINATION / output_name

    if not source.exists():
        raise RuntimeError(f"Export introuvable : {source}")

    if target.exists():
        raise RuntimeError(
            f"Destination deja presente : {target}. "
            "Aucune modification effectuee."
        )

    files = 0

    for item in source.rglob("*"):
        if not item.is_file():
            continue

        relative = item.relative_to(source)

        # Ne pas copier les metadonnees de l'item original
        if ".platform" in relative.parts or ".pbi" in relative.parts:
            continue

        content = item.read_bytes()
        destination = target / relative

        # Modifier uniquement les deux partitions du modele
        if (
            output_name == "SemanticModel"
            and relative.as_posix() in (
                "definition/tables/station_latest.tmdl",
                "definition/tables/station_history.tmdl",
            )
        ):
            text = content.decode("utf-8")

            if text.count(OLD_DATABASE) != 1:
                raise RuntimeError(
                    f"Connexion SQL inattendue : {relative}"
                )

            content = text.replace(
                OLD_DATABASE, NEW_DATABASE
            ).encode("utf-8")

            destination = destination.with_name(
                destination.name + ".tmpl"
            )

        # Relier le rapport au futur modele Terraform
        if (
            output_name == "Report"
            and relative.as_posix() == "definition.pbir"
        ):
            definition = json.loads(content)

            definition["datasetReference"] = {
                "byConnection": {
                    "connectionString": (
                        "semanticmodelid={{ .SemanticModelId }}"
                    )
                }
            }

            content = json.dumps(
                definition,
                indent=2,
                ensure_ascii=False,
            ).encode("utf-8")

            destination = destination.with_name(
                destination.name + ".tmpl"
            )

        destination.parent.mkdir(
            parents=True, exist_ok=True
        )
        destination.write_bytes(content)
        files += 1

    print(f"{output_name} : {files} fichiers prepares")


prepare("semantic-model", "SemanticModel")
prepare("report", "Report")

print("Definitions Power BI pretes pour Terraform.")
