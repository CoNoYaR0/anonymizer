# -*- coding: utf-8 -*-
"""
Flux : HTML → id_to_text_map → classification regex → JSON annoté → prompt GPT‑5 → JSON Liquid

Ce fichier contient :
- PROMPT_GPT5 : le prompt à envoyer à GPT‑5 (une fois formaté avec .format(...))
- REGEX_CORE   : noyau de regex (Python) pour détecter les entités clés
- classify_text / annotate_map : logique d’exemple pour labelliser les IDs
- build_prompt : helper pour formater le prompt final
"""

import json
from typing import Dict

# ---------------------------------------------------------------------------
# 1) PROMPT GPT-4o (détection → mapping Liquid)
# ---------------------------------------------------------------------------

PROMPT_GPT4 = """\
You are a templating expert. Your task is to map re-assembled, coherent lines of text from a CV to their corresponding Liquid placeholders.

You will receive a JSON object where each key is a unique `block-id` and the value is the clean text content from that block.

Your task:
- Analyze the text for each `block-id`.
- Produce a JSON object mapping the `block-id` to its correct Liquid placeholder.
- **Only include IDs for dynamic values.** Exclude any text that is a static label (e.g., "Experience", "Education", "Missions :", etc.).
- The text has been pre-processed. Trust that each value is a single, coherent piece of information.
- For a line like "WSN Ingénieure en informatique 16 ans d’expérience Mission au sein de TeamWill Consulting", you must extract all placeholders.

### Rules & Conventions
- Keep keys identical to the input IDs.
- Use consistent Liquid paths:
  - Candidate Info:
    - Full name → `{{ candidate.full_name }}`
    - Initials → `{{ candidate.initials }}`
    - Job title → `{{ candidate.current_job.title }}`
    - Company → `{{ candidate.current_job.company }}`
    - Years of experience → `{{ candidate.years_of_experience }}`
  - Experience Section:
    - Title → `{{ experience[i].title }}`
    - Company → `{{ experience[i].company }}`
    - Dates → `{{ experience[i].dates }}`
    - Context → `{{ experience[i].context }}`
    - Tasks/Missions → `{{ experience[i].tasks[j] }}`
    - Technologies → `{{ experience[i].technologies }}`
  - Education Section:
    - Degree/Title → `{{ education[i].degree }}`
    - School/Issuer → `{{ education[i].school }}`
    - Dates → `{{ education[i].date }}`
  - Skills Section:
    - For a line of skills like "HTML5, CSS, Typescript, Angular", map the entire line to the appropriate placeholder, e.g., `{{ skills.languages }}` or `{{ skills.frameworks }}`.
- Preserve arrays: for repeating blocks (like jobs or tasks), assume index `i` or `j`.

### Input Data
{TEXT_BLOCKS}

### Output
Return ONLY the final JSON mapping: `{{ "block-id": "Liquid placeholder" }}`.
If a single block contains multiple placeholders, combine them. For example, for "16 ans d’expérience chez Acme", the output for that block should be `{{ candidate.years_of_experience }} chez {{ experience[0].company }}`.
"""

def build_prompt(text_blocks: Dict[str, str]) -> str:
    """
    Formats the prompt with the new re-assembled text blocks map.
    """
    return PROMPT_GPT4.format(
        TEXT_BLOCKS=json.dumps(text_blocks, ensure_ascii=False, indent=2)
    )

# The old regex and classification logic is no longer needed, as the pre-processor
# in template_builder.py and this simplified prompt handle the complexity.
