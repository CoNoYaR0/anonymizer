import os
import hashlib
import requests
import time
import sys
import base64
import json
import re
from typing import Optional, Dict, List, Any, Tuple
from dotenv import load_dotenv
from bs4 import BeautifulSoup, NavigableString
from openai import OpenAI

# ... (other imports and functions remain the same)
# Import caching functions from the database module
from . import database

# Load environment variables
load_dotenv()
CONVERTIO_API_KEY = os.getenv("CONVERTIO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# ... (_calculate_file_hash and convert_docx_to_html_and_cache are unchanged)
def _calculate_file_hash(file_content: bytes) -> str:
    """Calculates the SHA-256 hash of the file content."""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    return sha256_hash.hexdigest()

def convert_docx_to_html_and_cache(file_content: bytes) -> str:
    """
    Checks cache for HTML. If not found, converts DOCX to HTML via Convertio and caches it.
    """
    file_hash = _calculate_file_hash(file_content)
    print(f"Calculated hash: {file_hash}")

    cached_html = database.get_cached_html(file_hash)
    if cached_html:
        print("Found pre-converted HTML in cache.")
        return cached_html

    print("HTML not in cache. Converting with Convertio...")
    if not CONVERTIO_API_KEY:
        raise Exception("CONVERTIO_API_KEY is not set.")

    try:
        # Step 1: Start conversion using Base64 upload
        print("Step 1/3: Starting Convertio conversion with Base64 upload...")
        encoded_file = base64.b64encode(file_content).decode('ascii')

        start_response = requests.post(
            "https://api.convertio.co/convert",
            json={
                "apikey": CONVERTIO_API_KEY,
                "input": "base64",
                "file": encoded_file,
                "filename": "template.docx",
                "outputformat": "html"
            }
        )
        start_response.raise_for_status()
        response_json = start_response.json()
        print(f"DEBUG: Convertio start response: {response_json}")

        if response_json.get('error'):
             raise Exception(f"Convertio API Error on start: {response_json['error']}")

        conv_id = response_json["data"]["id"]

        # Step 2: Poll for conversion status
        print("Step 2/3: Polling for conversion status...")
        while True:
            status_response = requests.get(f"https://api.convertio.co/convert/{conv_id}/status")
            status_response.raise_for_status()
            status_data = status_response.json()["data"]

            if status_data["step"] == "finish":
                html_url = status_data["output"]["url"]
                break
            elif status_data["step"] == "error":
                raise Exception(f"Convertio API error during conversion: {status_data.get('error')}")

            print(f"Conversion in progress: {status_data['step']}...")
            time.sleep(2)

        # Step 3: Download the resulting HTML
        print("Step 3/3: Downloading converted HTML...")
        html_response = requests.get(html_url)
        html_response.raise_for_status()
        html_content = html_response.text

        # Cache the new HTML
        database.cache_html(file_hash, html_content)
        print("Saved new HTML to cache.")

        return html_content

    except requests.exceptions.RequestException as e:
        print(f"FATAL: An error occurred during Convertio API request: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response Status Code: {e.response.status_code}", file=sys.stderr)
            print(f"Response Body: {e.response.text}", file=sys.stderr)
        raise e
    except Exception as e:
        print(f"FATAL: An unexpected error occurred in convert_docx_to_html_and_cache: {e}", file=sys.stderr)
        raise e


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
    - Location → `{{{{ candidate.location }}}}`
    - Email → `{{{{ candidate.email }}}}`, Phone → `{{{{ candidate.phone }}}}`
  - Experience (array, order preserved top→down):
    - Title → `{{{{ experience[i].title }}}}`
    - Company → `{{{{ experience[i].company }}}}`
    - Date start/end → `{{{{ experience[i].date_start }}}}`, `{{{{ experience[i].date_end }}}}` (if missing end, omit the ID or map to `null`)
    - Context (optional) → `{{{{ experience[i].context }}}}`
    - Missions / tasks (0..N) → `{{{{ experience[i].tasks[j] }}}}`
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


def _get_ai_replacement_map(id_to_text_map: Dict[str, str]) -> Dict[str, str]:
    """
    Sends the ID-to-text map to the AI after pre-processing with regex
    and gets back an ID-to-Liquid map.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    # 1. Classification par regex
    print("Annotating text map with regex...")
    annotations = annotate_map(id_to_text_map)

    # 2. Construire le prompt pour GPT-5
    print("Building prompt for GPT-5...")
    prompt = build_prompt(
        id_to_text_map=id_to_text_map,
        annotations=annotations
    )

    # 3. Appel à GPT-5
    print("Calling OpenAI API to get placeholder map...")
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    response_content = response.choices[0].message.content
    print(f"DEBUG: OpenAI response: {response_content}")

    try:
        return json.loads(response_content)
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON from OpenAI response.")


def inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses a token-efficient, ID-based hybrid approach to inject Liquid placeholders.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    print("Parsing HTML and preparing for AI injection...")
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Add unique IDs to all text nodes and create an ID-to-text map
    id_to_text_map = {}
    node_counter = 0
    for text_node in soup.find_all(string=True):
        if text_node.strip() and not isinstance(text_node.parent, (BeautifulSoup, NavigableString)) and text_node.parent.name not in ['style', 'script']:
            node_id = f"liquid-node-{node_counter}"
            id_to_text_map[node_id] = text_node.strip()
            text_node.parent[f"data-liquid-id"] = node_id
            node_counter += 1

    if not id_to_text_map:
        print("No text nodes found to process.")
        return str(soup)

    # 2. Get the replacement map from the AI
    id_to_liquid_map = _get_ai_replacement_map(id_to_text_map)

    # 3. Replace content and remove IDs
    print("Replacing content with Liquid placeholders...")
    for node_id, liquid_variable in id_to_liquid_map.items():
        element = soup.find(attrs={f"data-liquid-id": node_id})
        if element:
            # Clear the element and add the new Liquid variable
            element.clear()
            element.append(NavigableString(liquid_variable))

    # 4. Clean up all the data-liquid-id attributes
    for element in soup.find_all(attrs={"data-liquid-id": True}):
        del element["data-liquid-id"]

    return str(soup)


def create_and_inject_from_docx(file_content: bytes) -> str:
    """
    Orchestrates the entire template creation process from a DOCX file.
    1. Converts DOCX to HTML (using cache if available).
    2. Injects Liquid placeholders into the HTML.
    Returns the final Liquid template as a string.
    """
    print("Starting full template creation workflow...")

    # Step 1: Convert DOCX to HTML
    html_content = convert_docx_to_html_and_cache(file_content)
    if not html_content:
        raise Exception("Failed to get HTML content from DOCX.")

    # Step 2: Inject Liquid placeholders
    final_template = inject_liquid_placeholders(html_content)
    if not final_template:
        raise Exception("Failed to inject Liquid placeholders.")

    print("Full template creation workflow completed successfully.")
    return final_template
