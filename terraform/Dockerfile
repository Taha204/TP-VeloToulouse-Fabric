
# Étape 1 : récupérer Terraform
FROM hashicorp/terraform:1.17.2 AS terraform_binary

# Étape 2 : utiliser Azure CLI comme image principale
FROM mcr.microsoft.com/azure-cli:azurelinux3.0

# Copier Terraform dans notre image finale
COPY --from=terraform_binary /bin/terraform /usr/local/bin/terraform

# Définir le répertoire de travail
WORKDIR /workspace

# Ouvrir un terminal Bash par défaut
CMD ["/bin/bash"]
