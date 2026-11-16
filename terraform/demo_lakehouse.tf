
# Lakehouse de demonstration avec support des schemas
# Compatible avec la destination dbo.station_raw

resource "fabric_lakehouse" "iac_demo" {
  workspace_id = data.fabric_workspace.velotoulouse.id

  display_name = "LH_VeloToulouse_IaC_Demo"

  description = "Lakehouse de demonstration cree et gere avec Terraform pour le projet VeloToulouse."

  configuration = {
    enable_schemas = true
  }
}

output "demo_lakehouse_id" {
  value = fabric_lakehouse.iac_demo.id
}
