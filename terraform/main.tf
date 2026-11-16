
# Récupérer un workspace Fabric existant
# Aucune ressource n'est créée.

data "fabric_workspace" "velotoulouse" {
  id = "cb67eeef-0714-4dab-9b0f-6faea05bef24"

  skip_capacity_state_validation = true
}

# Afficher les informations récupérées
output "workspace_name" {
  value = data.fabric_workspace.velotoulouse.display_name
}

output "workspace_id" {
  value = data.fabric_workspace.velotoulouse.id
}
