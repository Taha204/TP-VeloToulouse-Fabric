
import base64
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

API = "https://api.fabric.microsoft.com/v1"

WORKSPACE_ID = "cb67eeef-0714-4dab-9b0f-6faea05bef24"
MODEL_ID = "40d0b9e6-3659-45f2-8fb1-fd28e44dba9b"
REPORT_ID = "91ffcfbb-29a7-4f4a-a0e2-73df8d298555"

# Dossier ignore par Git : export brut potentiellement sensible.
OUTPUT = Path("/workspace/.secrets/powerbi-original")

token = subprocess.check_output(
    [
        "az", "account", "get-access-token",
        "--resource", "https://api.fabric.microsoft.com",
        "--query", "accessToken",
        "-o", "tsv",
    ],
    text=True,
).strip()


def api_request(url, method="GET"):
    request = urllib.request.Request(
        url,
        data=b"" if method == "POST" else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
            return (
                response.status,
                response.headers,
                json.loads(body) if body else {},
            )
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Erreur Fabric HTTP {error.code}: {details[:1000]}"
        ) from None


def get_definition(url):
    status, headers, data = api_request(url, "POST")

    if status == 200:
        return data

    if status != 202:
        raise RuntimeError(f"Statut inattendu : {status}")

    operation_id = headers.get("x-ms-operation-id")
    if not operation_id:
        raise RuntimeError("Identifiant d'operation Fabric absent")

    for attempt in range(30):
        time.sleep(5)

        _, _, state = api_request(
            f"{API}/operations/{operation_id}"
        )
        status_name = state.get("status")

        print(f"  Operation Fabric : {status_name}")

        if status_name == "Succeeded":
            _, _, result = api_request(
                f"{API}/operations/{operation_id}/result"
            )
            return result

        if status_name in ("Failed", "Cancelled"):
            raise RuntimeError(
                f"Operation Fabric terminee : {status_name}"
            )

    raise TimeoutError(
        "L'export Fabric n'est pas encore termine"
    )


def export(name, url):
    print(f"\nExport : {name}")

    data = get_definition(url)
    definition = data.get("definition", {})
    parts = definition.get("parts", [])

    if not parts:
        raise RuntimeError(
            f"Aucune definition retournee pour {name}"
        )

    target = OUTPUT / name
    target.mkdir(parents=True, exist_ok=True)

    print("Format :", definition.get("format", "non precise"))
    print("Nombre de fichiers :", len(parts))

    for part in parts:
        path = PurePosixPath(part["path"])

        if (
            path.is_absolute()
            or ".." in path.parts
            or part.get("payloadType") != "InlineBase64"
        ):
            raise RuntimeError(f"Partie invalide : {path}")

        destination = target.joinpath(*path.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)

        content = base64.b64decode(
            part["payload"], validate=True
        )
        destination.write_bytes(content)

        print(f"  - {path} ({len(content)} octets)")

    print(f"Export {name} termine.")


export(
    "semantic-model",
    (
        f"{API}/workspaces/{WORKSPACE_ID}"
        f"/semanticModels/{MODEL_ID}/getDefinition?format=TMDL"
    ),
)

export(
    "report",
    (
        f"{API}/workspaces/{WORKSPACE_ID}"
        f"/reports/{REPORT_ID}/getDefinition"
    ),
)

print("\nTous les exports sont termines.")
