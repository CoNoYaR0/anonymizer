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
You are a templating expert. Your task is to map text values from a CV to their corresponding Liquid placeholders.

You will receive a JSON object. Each key is a unique `liquid-node-id`. The value for each key is another JSON object containing two fields:
1.  `text`: The raw text content from the HTML node.
2.  `section`: The document section this text was found in (e.g., "header", "experience", "skills", "education").

Your task:
- Analyze the `text` and its `section` context.
- Produce a JSON object mapping the original `liquid-node-id` to its correct Liquid placeholder.
- **Only include IDs for dynamic values.** Exclude any text that is a static label (like "Experience", "Education", "Missions :", etc.).
- Use the context provided by the `section` field to make more accurate decisions. For example, a job title in the "header" section is likely the candidate's current role.
- Output **ONLY** a valid JSON object.

### Rules & Conventions
- Keep keys identical to the input IDs.
- Use consistent Liquid paths:
  - Candidate Info (usually in "header" section):
    - Full name → `{{{{ candidate.full_name }}}}`
    - Initials → `{{{{ candidate.initials }}}}`
    - Current job title → `{{{{ candidate.current_job.title }}}}`
    - Current company → `{{{{ candidate.current_job.company }}}}`
    - Years of experience → `{{{{ candidate.years_of_experience }}}}`
    - Location → `{{{{ candidate.location }}}}`
    - Email → `{{{{ candidate.email }}}}`, Phone → `{{{{ candidate.phone }}}}`
  - Experience Section (texts from "experience" section):
    - Title → `{{{{ experience[i].title }}}}`
    - Company → `{{{{ experience[i].company }}}}`
    - Dates → `{{{{ experience[i].dates }}}}`
    - Context → `{{{{ experience[i].context }}}}`
    - Tasks/Missions → `{{{{ experience[i].tasks[j] }}}}`
    - Technologies → `{{{{ experience[i].technologies }}}}`
  - Education Section (texts from "education" section):
    - Degree/Title → `{{{{ education[i].degree }}}}`
    - School/Issuer → `{{{{ education[i].school }}}}`
    - Dates → `{{{{ education[i].date }}}}`
    - URL → `{{{{ certifications[i].url }}}}`
  - Skills Section (texts from "skills" section):
    - Languages → `{{{{ skills.languages }}}}`
    - Frameworks → `{{{{ skills.frameworks }}}}`
    - Databases → `{{{{ skills.databases }}}}`
    - Cloud → `{{{{ skills.cloud }}}}`
    - Tools → `{{{{ skills.tools }}}}`
- Preserve arrays: for repeating blocks (like jobs or tasks), assume index `i` or `j`.

### Input Data
{CONTEXT_MAP}

### Output
Return ONLY the final JSON mapping: ID → Liquid placeholder.
"""

def build_prompt(context_map: Dict[str, Dict[str, str]]) -> str:
    """
    Formats the prompt with the new context-rich map.
    """
    return PROMPT_GPT5.format(
        CONTEXT_MAP=json.dumps(context_map, ensure_ascii=False, indent=2)
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

    # Labels statiques (sections) à exclure
    "static_label": [
        re.compile(r"^\s*(expérience|experience|éducation|formation|certifications?|compétences|skills)\s*$", re.I),
        re.compile(r"^\s*(backend|frontend|langages?|frameworks?|outils|tools|cloud|databases?)\s*$", re.I),
    ],
}

# ---------------------------------------------------------------------------
# 3) COMMENT LES UTILISER (logique de base)
# ---------------------------------------------------------------------------

# The old classification logic is no longer needed as context is now
# determined programmatically in the pre-processing step.
# The AI will now use the 'section' field directly.
pass
