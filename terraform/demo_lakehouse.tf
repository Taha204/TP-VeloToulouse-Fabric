
# Lakehouse de démonstration Terraform
# Indépendant du pipeline VéloToulouse existant

resource "fabric_lakehouse" "iac_demo" {
  workspace_id = data.fabric_workspace.velotoulouse.id

  display_name = "LH_VeloToulouse_IaC_Demo"

  description = "Lakehouse de demonstration cree et gere avec Terraform pour le projet VeloToulouse."
}

output "demo_lakehouse_id" {
  value = fabric_lakehouse.iac_demo.id
}
