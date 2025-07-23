Write-Host "update git"
git pull 
# Afficher le statut Git
Write-Host "État actuel du dépôt :"
git status

# Ajouter tous les fichiers
git add .
Write-Host "Fichiers ajoutés à l'index."

# Demander le message de commit
$commitMessage = Read-Host "Message du commit"

# Commit avec le message
git commit -m "$commitMessage"
Write-Host "Commit effectué avec le message : $commitMessage"

# Push sur la branche main
git push origin main
Write-Host "Modifications poussées sur la branche 'main'."
