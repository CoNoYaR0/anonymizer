Plan complet pour le projet CV Anonymizer (copier-coller dans Jules)
🎯 Objectif général
Créer une plateforme web pour anonymiser automatiquement des CV, destinés aux sociétés de consulting,
afin de masquer toute information personnelle en conservant uniquement compétences, expériences, diplômes, et technologies.
________________________________________
📌 Phases de développement (fragmentées pour test progressif)
Phase 1 : MVP Technique (OCR → JSON brut)
Objectif : Tester l’extraction OCR et NER sur un fichier PDF
•	Frontend minimal (upload uniquement, React sur Netlify)
•	Backend API (FastAPI Python sur Render)
•	OCR avec Tesseract (PDF vers texte brut)
•	Extraction simple avec spaCy FR (nom, contact, expériences, compétences)
•	Stockage temporaire sur Supabase Storage/Postgres
Prompt Jules :
# Repo : “anonymizer”
- Installer FastAPI, Tesseract, spaCy (fr_core_news_md)
- Endpoint POST /upload pour recevoir un PDF
- Stocker fichier sur Supabase Storage
- Convertir PDF vers texte brut avec Tesseract
- Extraire NER (spaCy FR) et regex mail/tel, retourner JSON basique structuré.
- Stocker résultat extraction JSON dans Supabase DB
________________________________________
Phase 2 : Anonymisation et génération document
Objectif : Transformer le JSON extrait en document anonymisé (HTML → DOCX)
•	Anonymisation : pseudonymiser noms (initiales), placeholder contacts
•	Injection JSON dans un template HTML simple (avec Jinja2)
•	Générer fichier DOCX depuis HTML ou directement via python-docx
•	Téléchargement via frontend minimal
Prompt Jules :
# Repo : “anonymizer”
- Créer fonction anonymisation (initiales nom, placeholders mails/tel)
- Créer route POST /anonymize qui reçoit JSON brut, retourne HTML anonymisé
- Générer DOCX anonymisé via python-docx
- Stocker DOCX sur Supabase Storage
- Générer lien téléchargement sécurisé (expire après 24h)
________________________________________
Phase 3 : Frontend avancé et gestion utilisateur
Objectif : Créer UI complète : comptes clients, historique des CV, gestion des templates HTML
•	React + Tailwind CSS (Netlify)
•	Authentification via Supabase Auth (compte client)
•	Tableau de bord utilisateur : uploads, historique
•	Upload de templates personnalisés par utilisateur
Prompt Jules :
# Repo : “anonymizer”
- Configurer React/Tailwind sur Netlify avec Supabase Auth
- Créer UI upload CV (drag & drop)
- Ajouter historique téléchargements utilisateurs
- Permettre upload personnalisé template HTML
- Interactions via API Render FastAPI backend
________________________________________
Phase 4 : Intégration d’un LLM open-source pour affiner l’extraction
Objectif : Améliorer l’extraction avec un LLM open-source gratuit (Mistral) hébergé sur Hugging Face
•	Affiner extraction données (compétences complexes, technologies)
•	Utiliser Hugging Face inference API gratuite (ex. Mistral 7B)
•	Stocker résultat affiné dans Supabase
Prompt Jules :
# Repo : “anonymizer”
- Ajouter call API Hugging Face inference (Mistral-7B) après extraction spaCy
- Prompt LLM pour extraire/structurer précisément expériences/compétences/technologies
- Gérer fallback en cas de downtime API Hugging Face
- Stocker réponse JSON affiné dans Supabase DB
Gratuit au départ : Hugging Face free inference API (limité mais suffisant au début).
Passage payant ensuite : Hugging Face Pro ($9/mois) ou OpenAI GPT-4 (~$0.03/1000 tokens).
________________________________________
Phase 5 : Passage en production sécurisée
Objectif : Sécuriser et scaler l’app en prod réelle
•	CI/CD via GitHub Actions
•	Surveillance/monitoring Render
•	Backup régulier Supabase
•	RGPD : logs accès, purge automatique CV après X jours
Prompt Jules :
# Repo : “anonymizer”
- Ajouter CI/CD GitHub Actions (tests, linting, déploiement Render auto)
- Mettre en place monitoring et alertes basiques (Render)
- Programmer tâche périodique pour purge automatique CV et JSON (>30 jours)
- Enregistrer logs accès anonymisés dans Supabase pour audit RGPD
________________________________________
🌐 Workflow Tech global
Frontend (Netlify) ↔ Backend API (Render) ↔ Supabase (DB+Storage)
⚙️ Stack finale retenue :
•	Frontend : React, Tailwind (Netlify)
•	Backend : FastAPI Python (Render)
•	OCR : Tesseract + Poppler
•	Extraction : spaCy FR + HuggingFace LLM (Mistral gratuit puis GPT-4 payant)
•	DB & Storage : Supabase (Postgres+Storage+Auth)
•	Templating : HTML → DOCX via python-docx/Jinja2

