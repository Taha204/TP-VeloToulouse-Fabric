
locals {
  powerbi_report_path = "${path.module}/definitions/PowerBI/Report"
}

resource "fabric_report" "iac_demo" {
  workspace_id = data.fabric_workspace.velotoulouse.id

  display_name = "VeloToulouse_Dashboard_IaC_Demo"
  description  = "Rapport Power BI de demonstration deploye avec Terraform."

  format                    = "PBIR"
  definition_update_enabled = true

  definition = merge(
    {
      for path in fileset(local.powerbi_report_path, "**") :
      path => {
        source          = "${local.powerbi_report_path}/${path}"
        processing_mode = "None"
      }
      if !endswith(path, ".tmpl")
    },
    {
      "definition.pbir" = {
        source = "${local.powerbi_report_path}/definition.pbir.tmpl"
        tokens = {
          SemanticModelId = fabric_semantic_model.iac_demo.id
        }
      }
    }
  )
}

output "demo_report_id" {
  value = fabric_report.iac_demo.id
}
