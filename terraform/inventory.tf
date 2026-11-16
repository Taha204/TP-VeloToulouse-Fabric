
# Inventaire des ressources Fabric existantes
# Lecture seule : aucune création ni modification.

# 1. Ingestion
data "fabric_eventstream" "velotoulouse" {
  workspace_id = data.fabric_workspace.velotoulouse.id
  id           = "bd3bcd5a-7771-46d9-96a1-280f5cfa1d99"
}

# 2. Stockage
data "fabric_lakehouse" "velotoulouse" {
  workspace_id = data.fabric_workspace.velotoulouse.id
  id           = "74682ba6-6374-4e0e-8489-c738f99dcf3b"
}

# 3. Transformation
data "fabric_notebook" "transformation" {
  workspace_id = data.fabric_workspace.velotoulouse.id
  id           = "5173d569-fb76-4ff1-8e04-26ec1e90ad8d"
}

# Résumé de notre infrastructure
output "pipeline_fabric" {
  value = {
    eventstream_id = data.fabric_eventstream.velotoulouse.id
    lakehouse_id   = data.fabric_lakehouse.velotoulouse.id
    notebook_id    = data.fabric_notebook.transformation.id
  }
}


# 4. Visualisation Power BI
data "fabric_report" "dashboard" {
  workspace_id = data.fabric_workspace.velotoulouse.id
  id           = "91ffcfbb-29a7-4f4a-a0e2-73df8d298555"
}

# 5. Modèle sémantique Power BI
data "fabric_semantic_model" "dashboard" {
  workspace_id = data.fabric_workspace.velotoulouse.id
  id           = "40d0b9e6-3659-45f2-8fb1-fd28e44dba9b"
}

# Résumé Power BI
output "powerbi_fabric" {
  value = {
    report_id         = data.fabric_report.dashboard.id
    semantic_model_id = data.fabric_semantic_model.dashboard.id
  }
}
