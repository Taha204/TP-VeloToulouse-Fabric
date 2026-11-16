
# Copie du notebook de transformation de Taha
# Déployée dans le workspace existant
# et reliée au Lakehouse créé par Terraform.

resource "fabric_notebook" "iac_demo" {
  workspace_id = data.fabric_workspace.velotoulouse.id

  display_name = "NB_VeloToulouse_Transform_IaC_Demo"

  description = "Copie de demonstration du notebook de transformation VeloToulouse, deployee avec Terraform."

  format                    = "ipynb"
  definition_update_enabled = true

  definition = {
    "notebook-content.ipynb" = {
      source = "${path.module}/definitions/NB_VeloToulouse_Transform/NB_VeloToulouse_Transform.ipynb.tmpl"

      tokens = {
        WorkspaceId   = data.fabric_workspace.velotoulouse.id
        LakehouseId   = fabric_lakehouse.iac_demo.id
        LakehouseName = fabric_lakehouse.iac_demo.display_name
      }
    }
  }
}

output "demo_notebook_id" {
  value = fabric_notebook.iac_demo.id
}
