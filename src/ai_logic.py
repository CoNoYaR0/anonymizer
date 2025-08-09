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

You will receive a JSON object where each key is a unique `block-id` from the document, and the value is the clean, coherent text content from that block. The text has been pre-processed to fix fragmentation issues.

Your task:
- Analyze the text for each `block-id`.
- Produce a JSON object mapping the `block-id` to its correct Liquid placeholder.
- **Only include IDs for dynamic values.** Exclude any text that is a static label (e.g., "Experience", "Education", "Missions :", etc.).
- If a single line of text contains multiple dynamic values, you MUST combine them. For example, for a block with text "WSN Ingénieure en informatique 16 ans d’expérience", your output for that block's ID should be "{{ candidate.initials }} {{ candidate.current_job.title }} {{ candidate.years_of_experience }}".

### Rules & Conventions
- Keep keys identical to the input IDs.
- Use consistent Liquid paths. The main categories are `candidate`, `experience[i]`, `education[i]`, and `skills`.
- The first job title and company listed are usually the current ones (`candidate.current_job`).
- For repeating items like jobs or tasks, use the correct index `[i]` or `[j]`.

### Input Data
{TEXT_BLOCKS}

### Output
Return ONLY the final JSON mapping: `{{ "block-id": "Liquid placeholder" }}`.
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
