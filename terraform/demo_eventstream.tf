
# Copie de l'Eventstream de Karl
# Destination : Lakehouse de demonstration Terraform

resource "fabric_eventstream" "iac_demo" {
  workspace_id = data.fabric_workspace.velotoulouse.id

  display_name = "ES_VeloToulouse_IaC_Demo"

  description = "Copie de demonstration de l'Eventstream VeloToulouse, deployee avec Terraform."

  format                    = "Default"
  definition_update_enabled = true

  definition = {
    "eventstream.json" = {
      source = "${path.module}/definitions/ES_VeloToulouse/eventstream.json.tmpl"

      tokens = {
        WorkspaceId = data.fabric_workspace.velotoulouse.id
        LakehouseId = fabric_lakehouse.iac_demo.id
      }
    }
  }
}

output "demo_eventstream_id" {
  value = fabric_eventstream.iac_demo.id
}
