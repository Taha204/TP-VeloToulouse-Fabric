
locals {
  powerbi_model_path = "${path.module}/definitions/PowerBI/SemanticModel"
}

resource "fabric_semantic_model" "iac_demo" {
  workspace_id = data.fabric_workspace.velotoulouse.id

  display_name = "VeloToulouse_Dashboard_IaC_Demo_Model"
  description  = "Modele semantique de demonstration deploye avec Terraform."

  format                    = "TMDL"
  definition_update_enabled = true

  definition = merge(
    {
      for path in fileset(local.powerbi_model_path, "**") :
      path => {
        source          = "${local.powerbi_model_path}/${path}"
        processing_mode = "None"
      }
      if !endswith(path, ".tmpl")
    },
    {
      for name in ["station_latest", "station_history"] :
      "definition/tables/${name}.tmdl" => {
        source = "${local.powerbi_model_path}/definition/tables/${name}.tmdl.tmpl"
        tokens = {
          LakehouseName = fabric_lakehouse.iac_demo.display_name
        }
      }
    }
  )
}

output "demo_semantic_model_id" {
  value = fabric_semantic_model.iac_demo.id
}
