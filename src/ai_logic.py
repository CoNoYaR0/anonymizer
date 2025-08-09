# -*- coding: utf-8 -*-
"""
Flux : HTML → id_to_text_map → classification regex → JSON annoté → prompt GPT‑5 → JSON Liquid

Ce fichier contient :
- PROMPT_GPT5 : le prompt à envoyer à GPT‑5 (une fois formaté avec .format(...))
- REGEX_CORE   : noyau de regex (Python) pour détecter les entités clés
- classify_text / annotate_map : logique d’exemple pour labelliser les IDs
- build_prompt : helper pour formater le prompt final
"""

import re
import json
from typing import Dict, List, Any, Tuple

# ---------------------------------------------------------------------------
# 1) PROMPT GPT‑5 (détection → mapping Liquid)
# ---------------------------------------------------------------------------

PROMPT_GPT5 = """\
You are a templating expert. You receive:
1) A JSON object mapping HTML node IDs to text content (id_to_text_map).
2) An optional JSON "annotations" object mapping the same IDs to detected types (e.g., "full_name", "job_title", "company", "date_range", etc.).

Your task:
- Produce a JSON object mapping the SAME IDs to Liquid placeholders **only for dynamic values**.
- Exclude IDs whose text is a static label (e.g., "Experience", "Education", "Compétences", section titles, separators).
- Output **ONLY** a valid JSON object (no prose).

### Rules & Conventions
- Keep keys identical to the input IDs.
- Use consistent Liquid paths:
  - Candidate:
    - Full name → `{{{{ candidate.full_name }}}}`
    - Initials (anonymization WSN rule) → `{{{{ candidate.initials }}}}`
      - **WSN rule**: initials = UPPER(last_name[0] + first_name[:2]).
        (Calcul will be handled outside the template; just map to `candidate.initials`.)
    - Current job title → `{{{{ candidate.current_job.title }}}}`
    - Current company → `{{{{ candidate.current_job.company }}}}`
    - Years of experience → `{{{{ candidate.years_of_experience }}}}`
    - Location → `{{{{ candidate.location }}}}`
    - Email → `{{{{ candidate.email }}}}`, Phone → `{{{{ candidate.phone }}}}`
  - Experience (array, order preserved top→down):
    - Title → `{{{{ experience[i].title }}}}`
    - Company → `{{{{ experience[i].company }}}}`
    - Date start/end → `{{{{ experience[i].date_start }}}}`, `{{{{ experience[i].date_end }}}}` (if missing end, omit the ID or map to `null`)
    - Context (optional) → `{{{{ experience[i].context }}}}`
    - Missions / tasks (0..N) → `{{{{ experience[i].tasks[j] }}}}`
    - Technologies → `{{{{ experience[i].technologies }}}}`
  - Education & certifications (arrays):
    - School / center → `{{{{ education[i].school }}}}` / `{{{{ certifications[i].issuer }}}}`
    - Degree / title → `{{{{ education[i].degree }}}}` / `{{{{ certifications[i].title }}}}`
    - Dates (optional) → `{{{{ education[i].date }}}}`, `{{{{ certifications[i].date }}}}`
    - URL (optional) → `{{{{ certifications[i].url }}}}`
  - Skills (can evolve):
    - Languages → `{{{{ skills.languages }}}}` (list)
    - Frameworks → `{{{{ skills.frameworks }}}}` (list)
    - Tools / Cloud / DBs → `{{{{ skills.tools }}}}`, `{{{{ skills.cloud }}}}`, `{{{{ skills.databases }}}}`
    - Functional skills → `{{{{ skills.functional }}}}` (list)
- If annotations are present, **respect them**. If they’re missing or ambiguous, infer conservatively.
- If the text is clearly static (headers, separators, generic labels), **exclude** that ID.
- Preserve arrays: for repeating blocks, assume index `i` (and `j` for tasks). If you suspect a repeating row, map consistently using `experience[i]` etc.
- If a field is dynamic but its content may be absent (e.g., end date, context, URL), still map it (the rendering engine can handle null/empty).

### Special Header Rules
- Text in the document header (near the candidate's name) often contains the current job title and company. These require special mapping.
- The job title in the header (e.g., "Ingénieure en informatique") MUST be mapped to `{{{{ experience[0].title }}}}`.
- Text containing "Mission au sein de..." should be parsed for the company name, and that company name MUST be mapped to `{{{{ experience[0].company }}}}`.

### Special Skills Rules
- The "Compétences techniques et fonctionnelles" section lists skills. The text following these category labels MUST be mapped to the correct `skills` placeholders.
- Map text after 'Langages & Frontend' to `{{{{ skills.languages }}}}`.
- Map text after 'Backend & Frameworks' to `{{{{ skills.frameworks }}}}`.
- Map text after 'Bases de données & Cache' to `{{{{ skills.databases }}}}`.
- Map text after 'DevOps & Cloud' to `{{{{ skills.cloud }}}}`.
- Map text after 'CI/CD & Outils' to `{{{{ skills.tools }}}}`.

### Inputs
id_to_text_map:
{ID_TO_TEXT_MAP}

annotations (optional):
{ANNOTATIONS}

### Output
Return ONLY the final JSON mapping: ID → Liquid placeholder (no additional text).
"""

def build_prompt(id_to_text_map: Dict[str, str],
                 annotations: Dict[str, Any] = None) -> str:
    """
    Formatte le prompt final pour GPT‑5.
    """
    return PROMPT_GPT5.format(
        ID_TO_TEXT_MAP=json.dumps(id_to_text_map, ensure_ascii=False, indent=2),
        ANNOTATIONS=json.dumps(annotations or {}, ensure_ascii=False, indent=2)
    )

# ---------------------------------------------------------------------------
# 2) NOYAU DE REGEX (Python style)
#    ⚠️ Ce sont des exemples – adapte-les à tes données/locale.
# ---------------------------------------------------------------------------

REGEX_CORE: Dict[str, List[re.Pattern]] = {
    # Noms complets (prénom nom / nom prénom) – large filet
    "full_name": [
        re.compile(r"^[A-ZÉÈÀÂÎ][a-zA-ZÀ-ÖØ-öø-ÿ'’\-]+(?:\s+[A-ZÉÈÀÂÎ][a-zA-ZÀ-ÖØ-öø-ÿ'’\-]+){1,3}$")
    ],

    # Candidate initials
    "initials": [
        re.compile(r"^\s*[A-Z]{2,3}\s*$")
    ],

    # Languages
    "languages": [
        re.compile(r"^\s*langues\b.*", re.I)
    ],

    # Job title courant – mots fréquents
    "job_title": [
        re.compile(r"\b(lead|senior|jr\.?|junior|staff|principal|architect|manager|engineer|developer|développeur|ingénieur|devops|ml|data|product|designer|cto|cto|cpo)\b", re.I),
    ],

    # Société / entreprise – heuristique simple (mots-clés)
    "company": [
        re.compile(r"\b(sas|sa|sarl|ltd|inc|corp|gmbh|spa|s\.?a\.?r\.?l\.?)\b", re.I),
    ],

    # Date simple
    "date": [
        re.compile(r"\b(?:\d{1,2}[/-])?(?:\d{1,2}[/-])?\d{2,4}\b"),  # très permissif
        re.compile(r"\b(?:janv\.?|févr\.?|mars|avr\.?|mai|juin|juil\.?|août|sept\.?|oct\.?|nov\.?|déc\.?|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}\b", re.I),
        re.compile(r"\b\d{4}\b")
    ],

    # Intervalle de dates
    "date_range": [
        re.compile(r"(?P<start>[^–\-→]+?)\s*(?:–|-|→|to|à)\s*(?P<end>[^–\-→]+?)$", re.I),
        re.compile(r"(?P<start>\b\d{4}\b)\s*[-–]\s*(?P<end>\b\d{4}\b)"),
    ],

    # Email, phone, URL
    "email": [re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)],
    "phone": [re.compile(r"\+?\d[\d .\-()]{7,}\d")],
    "url":   [re.compile(r"https?://[^\s]+", re.I)],

    # Ville (heuristique : mot capitalisé + éventuellement pays)
    "city": [
        re.compile(r"^[A-ZÉÈÀÂÎ][a-zà-öø-ÿ'’\-]+(?:,\s*[A-Z][a-z]+)?$"),
    ],

    # Éducation / Certification (mots-clés fréquents)
    "education": [
        re.compile(r"\b(école|université|master|licence|bachelor|bsc|msc|phd| ingénierie|dipl[oô]me)\b", re.I),
    ],
    "certification": [
        re.compile(r"\b(certification|certificate|certifié|aws certified|gcp professional|azure)\b", re.I),
    ],

    # Years of experience
    "years_of_experience": [
        re.compile(r"\b\d+\s+ans\s+d['’]expérience\b", re.I)
    ],

    # Technologies list
    "technologies": [
        re.compile(r"^\s*technologies\b.*", re.I)
    ],

    # Labels statiques (sections) à exclure
    "static_label": [
        re.compile(r"^\s*(expérience|experience|éducation|formation|certifications?|compétences|skills)\s*$", re.I),
        re.compile(r"^\s*(backend|frontend|langages?|frameworks?|outils|tools|cloud|databases?)\s*$", re.I),
    ],
}

# ---------------------------------------------------------------------------
# 3) COMMENT LES UTILISER (logique de base)
# ---------------------------------------------------------------------------

def classify_text(txt: str) -> List[str]:
    """
    Retourne la/les étiquette(s) probable(s) pour un texte donné.
    Heuristique simple : si "static_label" matche → on ne garde que static_label.
    Sinon on collecte les autres catégories qui matchent.
    """
    txt_norm = txt.strip()
    if not txt_norm:
        return []

    labels: List[str] = []
    # Static d’abord : s’il matche, on s’arrête là (on exclura au mapping).
    for p in REGEX_CORE["static_label"]:
        if p.search(txt_norm):
            return ["static_label"]

    for label, patterns in REGEX_CORE.items():
        if label == "static_label":
            continue
        for p in patterns:
            if p.search(txt_norm):
                labels.append(label)
                break  # évite la redondance intra-catégorie
    return labels


def annotate_map(id_to_text_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Parcourt le map id→texte, et retourne un JSON d’annotations :
      { "<id>": { "labels": [...], "raw": "<texte>" }, ... }
    """
    annotations: Dict[str, Any] = {}
    for _id, txt in id_to_text_map.items():
        labels = classify_text(txt or "")
        if labels:
            annotations[_id] = {"labels": labels, "raw": txt}
        else:
            annotations[_id] = {"labels": [], "raw": txt}
    return annotations


# ---------------------------------------------------------------------------
# 4) EXEMPLE D’UTILISATION
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # === Exemple d’entrée (à remplacer par ton vrai id_to_text_map issu du HTML) ===
    id_to_text_map_example = {
        "h_hero_name": "Wassim Sassi",
        "h_hero_job": "Senior Backend Engineer",
        "section_title_experience": "Expérience professionnelle",
        "exp1_company": "ACME SAS",
        "exp1_title": "Lead Python Developer",
        "exp1_dates": "Jan 2021 – Présent",
        "exp1_context": "Projet data realtime, équipe de 6.",
        "exp1_task_1": "Conception d'APIs REST.",
        "exp1_task_2": "CI/CD GitHub Actions.",
        "skills_lang": "Python, Go, JavaScript",
        "skills_fw": "Django, FastAPI, React",
        "education_1": "École Polytechnique",
        "cert_1": "AWS Certified Solutions Architect – Associate",
        "contact_email": "wassim@example.com",
        "contact_phone": "+216 20 123 456",
        "label_skills": "Compétences",
    }

    # 1) Classification par regex
    annotations = annotate_map(id_to_text_map_example)

    # 2) Construire le prompt pour GPT‑5 (mapping Liquid)
    prompt = build_prompt(
        id_to_text_map=id_to_text_map_example,
        annotations=annotations  # facultatif mais recommandé
    )

    # 3) Appel à GPT‑5 (pseudo-code, remplace par ton client réel)
    # response = gpt5.generate(prompt, model="gpt-5.1", temperature=0)
    # mapping_json = json.loads(response.text)

    # Pour debug local :
    print("=== PROMPT ENVOYÉ À GPT‑5 ===")
    print(prompt)

    print("\n=== ANNOTATIONS (aperçu) ===")
    print(json.dumps(annotations, ensure_ascii=False, indent=2))

    # 4) Exemple d’utilisation côté rendu :
    # - Tu calcules candidate.initials selon la règle WSN en backend :
    #     initials = (last_name[:1] + first_name[:2]).upper()
    # - Tu fournis au moteur Liquid un contexte tel que :
    # {
    #   "candidate": {
    #     "full_name": "...",
    #     "initials": "WSN",
    #     "current_job": {"title": "...", "company": "..."},
    #     "location": "...", "email": "...", "phone": "..."
    #   },
    #   "experience": [
    #     {
    #       "title": "...", "company": "...",
    #       "date_start": "2021-01", "date_end": null,
    #       "context": "...",
    #       "tasks": ["...", "..."]
    #     },
    #     ...
    #   ],
    #   "education": [...],
    #   "certifications": [...],
    #   "skills": {
    #     "languages": ["Python", "Go", "JavaScript"],
    #     "frameworks": ["Django", "FastAPI", "React"],
    #     "tools": [...], "cloud": [...], "databases": [...],
    #     "functional": [...]
    #   }
    # }
