# Project Overview: CV Anonymizer

## Contexte

### Pourquoi automatiser l’anonymisation de CV pour des sociétés de consulting ?

Dans le secteur du consulting, le volume de CV traités est conséquent. L'anonymisation manuelle est une tâche chronophage et sujette à des erreurs humaines. L'automatisation de ce processus permet de :

- **Gagner en efficacité** : Libérer du temps pour les équipes RH et les managers.
- **Réduire les biais** : Assurer une évaluation des compétences plus objective.
- **Protéger les données personnelles** : Se conformer aux réglementations en vigueur (RGPD).

### Quel problème métier cela résout ?

Ce projet vise à résoudre plusieurs problèmes majeurs :

- **Contacts directs non souhaités** : Éviter que les clients finaux ne contactent directement les candidats, court-circuitant ainsi la société de conseil.
- **Conformité RGPD** : Garantir que les données personnelles des candidats sont traitées dans le respect de la réglementation, en supprimant les informations identifiantes non nécessaires à l'évaluation des compétences.
- **Homogénéisation des candidatures** : Présenter les profils de manière uniforme, ce qui facilite la comparaison et l'évaluation par les opérationnels.

## Objectifs du MVP (Minimum Viable Product)

Le MVP se concentrera sur les fonctionnalités essentielles pour valider la solution :

1.  **Pseudonymisation du nom** : Remplacer le nom complet du candidat par ses initiales (ex. “Beji Khalil” → “BKH”).
2.  **Masquage des coordonnées** : Remplacer l'e-mail et le numéro de téléphone par des placeholders génériques (ex. `[email]` et `[téléphone]`).
3.  **Extraction et structuration du contenu** : Isoler et réorganiser les sections suivantes :
    *   Expériences professionnelles
    *   Compétences
    *   Cursus académique
    *   Technologies maîtrisées
4.  **Génération d'un document .DOCX** : Produire un CV anonymisé au format `.docx` en utilisant un template prédéfini pour garantir l'uniformité.

## Fonctionnalités

- **Upload de fichiers** : Interface simple pour importer des CV aux formats PDF et DOCX.
- **Traitement OCR** : Extraction du texte des CV scannés ou non textuels.
- **Anonymisation** : Suppression ou remplacement des données personnelles.
- **Restructuration** : Organisation du contenu selon le template défini.
- **Export** : Téléchargement du CV anonymisé au format DOCX.

## Architecture

### Stack technique envisagée

- **Backend** : Python avec le framework Flask pour la logique métier et l'API.
- **Traitement de texte** :
    - `Tesseract OCR` pour la reconnaissance optique de caractères.
    - `spaCy` (modèle français) pour la reconnaissance d'entités nommées (NER) et l'analyse sémantique.
    - `python-docx` pour la manipulation et la génération de fichiers .DOCX.
- **Frontend** : Application statique (HTML/CSS/JavaScript) pour l'interface utilisateur.
- **Base de données** : Supabase pour le stockage des métadonnées et le suivi des traitements.

### Déploiement

- **Backend** : Déploiement sur Render pour une gestion simplifiée.
- **Frontend** : Hébergement sur Netlify pour la performance et la facilité de déploiement.
- **Base de données** : Utilisation de Supabase en tant que service (DBaaS).

## Roadmap MVP

1.  **Phase 1 : Setup de l'environnement**
    *   Initialisation du projet Python/Flask.
    *   Mise en place de l'environnement de développement (Docker).
2.  **Phase 2 : Extraction de contenu**
    *   Intégration de Tesseract pour l'OCR.
    *   Développement du module d'extraction de texte brut à partir des PDF et DOCX.
3.  **Phase 3 : Anonymisation et structuration**
    *   Intégration de spaCy pour la détection des informations à anonymiser.
    *   Développement des algorithmes de pseudonymisation et de masquage.
    *   Logique de reconnaissance et de séparation des blocs (Expériences, Compétences, etc.).
4.  **Phase 4 : Génération du document final**
    *   Création du template DOCX.
    *   Intégration de `python-docx` pour remplir le template avec les données extraites et structurées.
5.  **Phase 5 : API et déploiement**
    *   Développement des endpoints de l'API Flask.
    *   Déploiement du backend sur Render.
    *   Mise en ligne du frontend sur Netlify.
    *   Configuration de la base de données Supabase.
6.  **Phase 6 : Tests et validation**
    *   Tests unitaires et d'intégration.
    *   Validation du MVP avec un volume cible de 1 à 3 CV par jour.
