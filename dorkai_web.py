# ============================================================================
#  dorkAI WEB вЂ” РіРµРЅРµСЂР°С‚РѕСЂ Google dorks СЃ РїРѕРјРѕС‰СЊСЋ РР: Р±СЌРєРµРЅРґ + РёРЅС‚РµСЂС„РµР№СЃ
#  Р’РЎРЃ Р’ РћР”РќРћРњ Р¤РђР™Р›Р•. РћР±С‹С‡РЅС‹Р№ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ: СЃРєР°С‡Р°Р» С„Р°Р№Р» -> Р·Р°РїСѓСЃС‚РёР» -> РіРѕС‚РѕРІРѕ.
#
#  РљРђРљ Р—РђРџРЈРЎРўРРўР¬ (3 С€Р°РіР°):
#    1) СѓСЃС‚Р°РЅРѕРІРёС‚Рµ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕРґРЅРѕР№ РєРѕРјР°РЅРґРѕР№:
#         pip install fastapi "uvicorn[standard]" openai orjson python-dotenv
#    2) СЃРѕР·РґР°Р№С‚Рµ СЂСЏРґРѕРј С„Р°Р№Р» ".env" Рё РІСЃС‚Р°РІСЊС‚Рµ РєР»СЋС‡ РІ СЃС‚СЂРѕРєСѓ:
#         DORKAI_API_KEY=sk-...
#       (РїРѕ Р¶РµР»Р°РЅРёСЋ: DORKAI_BASE_URL, DORKAI_MODEL)
#    3) Р·Р°РїСѓСЃС‚РёС‚Рµ:
#         python dorkai_web.py
#       Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё РѕС‚РєСЂРѕРµС‚СЃСЏ Р±СЂР°СѓР·РµСЂ РЅР° http://127.0.0.1:8765
#
#  Р­С‚РёРєР°: С‚РѕР»СЊРєРѕ Р·Р°РєРѕРЅРЅС‹Р№ OSINT РїСѓР±Р»РёС‡РЅРѕ РёРЅРґРµРєСЃРёСЂСѓРµРјРѕР№ РёРЅС„РѕСЂРјР°С†РёРё.
# ============================================================================

# ----------------------------------------------------------------------------
#  Р‘Р›РћРљ 1. РРњРџРћР РўР« (РІРЅРµС€РЅРёРµ Р±РёР±Р»РёРѕС‚РµРєРё СЃС‚Р°РІСЏС‚СЃСЏ С‡РµСЂРµР· pip)
# ----------------------------------------------------------------------------

import json                               # Р·Р°РїР°СЃРЅРѕР№ JSON-РїР°СЂСЃРµСЂ СЃС‚Р°РЅРґР°СЂС‚РЅРѕР№ Р±РёР±Р»РёРѕС‚РµРєРё
import os                                 # РґРѕСЃС‚СѓРї Рє РїРµСЂРµРјРµРЅРЅС‹Рј РѕРєСЂСѓР¶РµРЅРёСЏ
import sys                                # stdout/stderr РґР»СЏ С„РёРєСЃР° РєРѕРґРёСЂРѕРІРєРё Windows
import threading                          # РїРѕС‚РѕРє: РѕС‚РєСЂС‹С‚СЊ Р±СЂР°СѓР·РµСЂ, РЅРµ Р±Р»РѕРєРёСЂСѓСЏ СЃРµСЂРІРµСЂ
import time                               # РїР°СѓР·Р° РїРµСЂРµРґ РѕС‚РєСЂС‹С‚РёРµРј Р±СЂР°СѓР·РµСЂР°
import webbrowser                         # СЃРёСЃС‚РµРјРЅС‹Р№ Р±СЂР°СѓР·РµСЂ РёР· СЃС‚Р°РЅРґР°СЂС‚РЅРѕР№ Р±РёР±Р»РёРѕС‚РµРєРё
from pathlib import Path                  # РѕР±СЉРµРєС‚РЅР°СЏ СЂР°Р±РѕС‚Р° СЃ РїСѓС‚СЏРјРё (.env СЂСЏРґРѕРј СЃРѕ СЃРєСЂРёРїС‚РѕРј)
from typing import Any                    # Р°РЅРЅРѕС‚Р°С†РёСЏ В«С‡С‚Рѕ СѓРіРѕРґРЅРѕВ» РґР»СЏ СЃС‹СЂС‹С… РґР°РЅРЅС‹С…

import orjson                             # СЃРІРµСЂС…Р±С‹СЃС‚СЂС‹Р№ JSON (СЏРґСЂРѕ РЅР° Rust)
from dotenv import load_dotenv            # Р·Р°РіСЂСѓР·РєР° ".env"-С„Р°Р№Р»Р° РІ РѕРєСЂСѓР¶РµРЅРёРµ
from fastapi import FastAPI               # СЃРѕРІСЂРµРјРµРЅРЅС‹Р№ Р°СЃРёРЅС…СЂРѕРЅРЅС‹Р№ РІРµР±-С„СЂРµР№РјРІРѕСЂРє
from fastapi.responses import HTMLResponse  # РѕР±С‹С‡РЅР°СЏ HTML-СЃС‚СЂР°РЅРёС†Р° (РЅР°С€ С„СЂРѕРЅС‚РµРЅРґ)
from openai import AsyncOpenAI            # РѕС„РёС†РёР°Р»СЊРЅС‹Р№ async-SDK Рє OpenAI-СЃРѕРІРјРµСЃС‚РёРјС‹Рј API
from pydantic import BaseModel, Field     # СЃС‚СЂРѕРіР°СЏ РІР°Р»РёРґР°С†РёСЏ РІС…РѕРґРЅРѕРіРѕ JSON-Р·Р°РїСЂРѕСЃР°

# ----------------------------------------------------------------------------
#  Р‘Р›РћРљ 2. РќРђРЎРўР РћР™РљР: РєР»СЋС‡ С‡РёС‚Р°РµС‚СЃСЏ РўРћР›Р¬РљРћ РёР· РѕРєСЂСѓР¶РµРЅРёСЏ/.env (РЅРµ С…Р°СЂРґРєРѕРґРёРј!)
# ----------------------------------------------------------------------------

class Settings:                           # РїСЂРѕСЃС‚РѕР№ РєРѕРЅС‚РµР№РЅРµСЂ РЅР°СЃС‚СЂРѕРµРє РїСЂРёР»РѕР¶РµРЅРёСЏ
    def __init__(self) -> None:
        """Р§РёС‚Р°РµС‚ РїРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ; СЂРµР°Р»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ РїСЂРёРѕСЂРёС‚РµС‚РЅРµРµ .env-С„Р°Р№Р»Р°."""
        env_path = Path(__file__).resolve().parent / ".env"   # РёС‰РµРј .env СЂСЏРґРѕРј СЃРѕ СЃРєСЂРёРїС‚РѕРј
        if env_path.is_file():                                # РµСЃР»Рё С„Р°Р№Р» РµСЃС‚СЊ...
            load_dotenv(env_path)                             # ...Р·Р°РіСЂСѓР¶Р°РµРј РµРіРѕ РІ os.environ
        self.api_key: str = (                                 # СЃРµРєСЂРµС‚РЅС‹Р№ РєР»СЋС‡ РґРѕСЃС‚СѓРїР°
            os.getenv("DORKAI_API_KEY", "").strip()           # РѕСЃРЅРѕРІРЅРѕРµ РёРјСЏ РїРµСЂРµРјРµРЅРЅРѕР№
            or os.getenv("OPENAI_API_KEY", "").strip()        # Р·Р°РїР°СЃРЅРѕРµ СѓРЅРёРІРµСЂСЃР°Р»СЊРЅРѕРµ РёРјСЏ
        )
        self.base_url: str = (                                # Р°РґСЂРµСЃ OpenAI-СЃРѕРІРјРµСЃС‚РёРјРѕРіРѕ API
            os.getenv("DORKAI_BASE_URL", "").strip()
            or "https://api.openai.com/v1"                    # СЃРµСЂРІРёСЃ РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ
        )
        self.model_name: str = (                              # РёРјСЏ РјРѕРґРµР»Рё РіРµРЅРµСЂР°С†РёРё
            os.getenv("DORKAI_MODEL", "").strip() or "gpt-4o-mini"
        )
        self.request_timeout: float = float(                  # СЃРµРєСѓРЅРґ РѕР¶РёРґР°РЅРёСЏ РѕС‚РІРµС‚Р° РјРѕРґРµР»Рё
            os.getenv("DORKAI_REQUEST_TIMEOUT", "90")
        )
        self.temperature: float = float(                      # В«С‚РІРѕСЂС‡РµСЃРєР°СЏ СЃРІРѕР±РѕРґР°В» 0..1
            os.getenv("DORKAI_TEMPERATURE", "0.3")
        )

    @property                                             # РІС‹Р·С‹РІР°РµС‚СЃСЏ РєР°Рє Р°С‚СЂРёР±СѓС‚
    def is_ready(self) -> bool:                           # РєР»СЋС‡ СЂРµР°Р»СЊРЅРѕ Р·Р°РїРѕР»РЅРµРЅ?
        return bool(self.api_key.strip())


SETTINGS = Settings()                     # СЃРѕР·РґР°С‘Рј РЅР°СЃС‚СЂРѕР№РєРё РѕРґРёРЅ СЂР°Р· РїСЂРё СЃС‚Р°СЂС‚Рµ

# ----------------------------------------------------------------------------
#  Р‘Р›РћРљ 3. РџР РћРњРџРў: СЂРѕР»СЊ РР Рё Р¶С‘СЃС‚РєРёРµ РїСЂР°РІРёР»Р° С„РѕСЂРјР°С‚Р° РѕС‚РІРµС‚Р°
# ----------------------------------------------------------------------------

SYSTEM_PROMPT: str = (
    "You are an elite OSINT analyst who writes advanced Google search queries "
    "(so called 'Google Dorks') using search operators.\n"
    "Use a wide range of operators and combine them: site:, inurl:, intitle:, "
    "intext:, filetype:, ext:, before:, after:, cache:, related:, numrange/, "
    ".. ranges, * wildcard, \"quoted phrases\", -exclusion, AND/OR.\n"
    "Rules for every dork:\n"
    "- exactly one line, valid Google search syntax, no fabricated operators;\n"
    "- escalate from broad reconnaissance to precise targeted findings;\n"
    "- no duplicates and no trivial queries that any beginner would write;\n"
    "- only legal OSINT of publicly indexed information.\n"
    'Answer with STRICT JSON only: {"dorks": ['
    '{"query": "<one-line google query>", '
    '"purpose": "<РєСЂР°С‚РєРѕРµ РѕР±СЉСЏСЃРЅРµРЅРёРµ РїРѕ-СЂСѓСЃСЃРєРё>", '
    '"operators": ["<operator1>", "<operator2>"]}]}'
)

# ----------------------------------------------------------------------------
#  Р‘Р›РћРљ 4. Р РђР—Р‘РћР  РћРўР’Р•РўРђ РќР•Р™Р РћРЎР•РўР: РїСЂРѕРёР·РІРѕР»СЊРЅС‹Р№ С‚РµРєСЃС‚ -> С‡РёСЃС‚С‹Рµ РґР°РЅРЅС‹Рµ РґРѕСЂРєРѕРІ
# ----------------------------------------------------------------------------

def extract_json_dict(raw_text: str) -> dict[str, Any]:
    """Р’С‹С‚Р°СЃРєРёРІР°РµС‚ РїРµСЂРІС‹Р№ JSON-РѕР±СЉРµРєС‚ РёР· РѕС‚РІРµС‚Р° РјРѕРґРµР»Рё (РјРѕРґРµР»Рё Р»СЋР±СЏС‚ Р»РёС€РЅРёР№ С‚РµРєСЃС‚)."""
    text = raw_text.strip()                            # СѓР±РёСЂР°РµРј РїСЂРѕР±РµР»С‹ РїРѕ РєСЂР°СЏРј
    if "```" in text:                                  # markdown-С„РµРЅСЃ ```json ... ```?
        chunk = text.split("```")[1]                   # Р±РµСЂС‘Рј СЃРѕРґРµСЂР¶РёРјРѕРµ РјРµР¶РґСѓ С„РµРЅСЃР°РјРё
        if chunk.lower().startswith("json"):           # РјРµС‚РєР° СЏР·С‹РєР° Сѓ С„РµРЅСЃР°?
            chunk = chunk[4:]                          # РѕС‚СЂРµР·Р°РµРј СЃР»РѕРІРѕ "json"
        text = chunk.strip()                           # СЂР°Р±РѕС‚Р°РµРј РґР°Р»СЊС€Рµ СЃ СЌС‚РёРј РєСѓСЃРєРѕРј
    first, last = text.find("{"), text.rfind("}")      # РіСЂР°РЅРёС†С‹ С„РёРіСѓСЂРЅС‹С… СЃРєРѕР±РѕРє
    if first == -1 or last == -1:                      # СЃРєРѕР±РѕРє РЅРµС‚ вЂ” СЌС‚Рѕ РѕС€РёР±РєР° С„РѕСЂРјР°С‚Р°
        raise ValueError("Р’ РѕС‚РІРµС‚Рµ РјРѕРґРµР»Рё РЅРµ РЅР°Р№РґРµРЅ JSON-РѕР±СЉРµРєС‚.")
    candidate = text[first : last + 1]                 # СЃСЂРµР· СЃС‚СЂРѕРіРѕ РІРЅСѓС‚СЂРё {...}
    try:
        return orjson.loads(candidate)                 # Р±С‹СЃС‚СЂС‹Р№ РїР°СЂСЃРёРЅРі (orjson/Rust)
    except orjson.JSONDecodeError:                     # orjson СЃС‚СЂРѕРіРёР№, РїСЂРѕР±СѓРµРј РјСЏРіС‡Рµ
        return json.loads(candidate)                   # Р·Р°РїР°СЃРЅРѕР№ РїР°СЂСЃРµСЂ stdlib

def parse_dorks(raw_text: str) -> list[dict[str, Any]]:
    """РџСЂРµРІСЂР°С‰Р°РµС‚ С‚РµРєСЃС‚ РѕС‚РІРµС‚Р° РјРѕРґРµР»Рё РІ СЃРїРёСЃРѕРє СЃР»РѕРІР°СЂРµР№ СЃ РїРѕР»СЏРјРё query/purpose/operators."""
    payload = extract_json_dict(raw_text)              # С‚РµРєСЃС‚ -> СЃР»РѕРІР°СЂСЊ
    items = payload.get("dorks")                       # РґРѕСЃС‚Р°С‘Рј РјР°СЃСЃРёРІ РїРѕ РєР»СЋС‡Сѓ "dorks"
    if not isinstance(items, list):                    # РЅРµС‚ РјР°СЃСЃРёРІР° вЂ” С„РѕСЂРјР°С‚ РЅР°СЂСѓС€РµРЅ
        raise ValueError("Р’ РѕС‚РІРµС‚Рµ РјРѕРґРµР»Рё РЅРµС‚ РјР°СЃСЃРёРІР° 'dorks'.")
    cleaned: list[dict[str, Any]] = []                 # СЃСЋРґР° СЃР»РѕР¶РёРј РІР°Р»РёРґРЅС‹Рµ СЌР»РµРјРµРЅС‚С‹
    for item in items:                                 # РїСЂРѕРІРµСЂСЏРµРј РєР°Р¶РґС‹Р№ СЌР»РµРјРµРЅС‚ РІСЂСѓС‡РЅСѓСЋ
        if isinstance(item, dict) and isinstance(item.get("query"), str):
            cleaned.append({                           # СЃРѕР±РёСЂР°РµРј РЅРѕСЂРјР°Р»РёР·РѕРІР°РЅРЅС‹Р№ СЃР»РѕРІР°СЂСЊ
                "query": item["query"].strip(),        # СЃС‚СЂРѕРєР° Р·Р°РїСЂРѕСЃР° Р±РµР· РјСѓСЃРѕСЂР°
                "purpose": str(item.get("purpose", "")),   # РїРѕСЏСЃРЅРµРЅРёРµ С†РµР»Рё
                "operators": [str(op) for op in item.get("operators", [])],  # РѕРїРµСЂР°С‚РѕСЂС‹
            })
    if not cleaned:                                    # РЅРё РѕРґРЅРѕРіРѕ РєРѕСЂСЂРµРєС‚РЅРѕРіРѕ СЌР»РµРјРµРЅС‚Р°
        raise ValueError("РћС‚РІРµС‚ РјРѕРґРµР»Рё РЅРµ СЃРѕРґРµСЂР¶Р°Р» РЅРё РѕРґРЅРѕРіРѕ РєРѕСЂСЂРµРєС‚РЅРѕРіРѕ РґРѕСЂРєР°.")
    return cleaned                                     # РіРѕС‚РѕРІС‹Р№ СЃРїРёСЃРѕРє РґРѕСЂРєРѕРІ

# ----------------------------------------------------------------------------
#  Р‘Р›РћРљ 5. РЎР•РўР•Р’РћР™ РљР›РР•РќРў Рљ РњРћР”Р•Р›Р (Р°СЃРёРЅС…СЂРѕРЅРЅС‹Р№, РїРµСЂРµРёСЃРїРѕР»СЊР·СѓРµС‚ СЃРѕРµРґРёРЅРµРЅРёСЏ)
# ----------------------------------------------------------------------------

# РљР»РёРµРЅС‚ СЃРѕР·РґР°С‘Рј Р›Р•РќРР’Рћ: AsyncOpenAI РїР°РґР°РµС‚ СЃСЂР°Р·Сѓ, РµСЃР»Рё РєР»СЋС‡ РїСѓСЃС‚,
# Р° СЃРµСЂРІРµСЂ РґРѕР»Р¶РµРЅ Р·Р°РїСѓСЃС‚РёС‚СЊСЃСЏ Рё РїРѕРєР°Р·Р°С‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ РїРѕРЅСЏС‚РЅСѓСЋ РїРѕРґСЃРєР°Р·РєСѓ.
_llm_client = None                        # СЃСЋРґР° РїРѕР»РѕР¶РёРј РєР»РёРµРЅС‚Р° РїСЂРё РїРµСЂРІРѕРј Р·Р°РїСЂРѕСЃРµ


def get_llm_client() -> AsyncOpenAI:
    """РЎРѕР·РґР°С‘С‚ Р°СЃРёРЅС…СЂРѕРЅРЅРѕРіРѕ РєР»РёРµРЅС‚Р° LLM РѕРґРёРЅ СЂР°Р· Рё РІРѕР·РІСЂР°С‰Р°РµС‚ РµРіРѕ РїСЂРё РІСЃРµС… РІС‹Р·РѕРІР°С…."""
    global _llm_client                    # РіР»РѕР±Р°Р»СЊРЅР°СЏ РїРµСЂРµРјРµРЅРЅР°СЏ-РєСЌС€
    if _llm_client is None:               # РєР»РёРµРЅС‚ РµС‰С‘ РЅРµ СЃРѕР·РґР°РЅ?
        _llm_client = AsyncOpenAI(        # РѕРґРёРЅ РєР»РёРµРЅС‚ РЅР° РІСЃС‘ РІСЂРµРјСЏ СЂР°Р±РѕС‚С‹ СЃРµСЂРІРµСЂР°
            api_key=SETTINGS.api_key,     # РєР»СЋС‡ РёР· .env/РѕРєСЂСѓР¶РµРЅРёСЏ вЂ” РЅРёРєРѕРіРґР° РЅРµ РІ РєРѕРґРµ
            base_url=SETTINGS.base_url,   # Р°РґСЂРµСЃ СЃРµСЂРІРёСЃР° (OpenAI/Groq/OpenRouterвЂ¦)
            timeout=SETTINGS.request_timeout,  # СЃРµРєСѓРЅРґ РЅР° РѕР¶РёРґР°РЅРёРµ РѕС‚РІРµС‚Р°
            max_retries=2,                # Р°РІС‚Рѕ-РїРѕРІС‚РѕСЂ РїСЂРё СЃРµС‚РµРІС‹С… СЃР±РѕСЏС…/Р»РёРјРёС‚Р°С…
        )
    return _llm_client                    # РїРµСЂРµРёСЃРїРѕР»СЊР·СѓРµРј РіРѕС‚РѕРІРѕРµ СЃРѕРµРґРёРЅРµРЅРёРµ

async def ask_model(topic: str, count: int) -> list[dict[str, Any]]:
    """РћС‚РїСЂР°РІР»СЏРµС‚ РїСЂРѕРјРїС‚С‹ РІ РјРѕРґРµР»СЊ Рё РІРѕР·РІСЂР°С‰Р°РµС‚ СЂР°Р·РѕР±СЂР°РЅРЅС‹Р№ СЃРїРёСЃРѕРє РґРѕСЂРєРѕРІ."""
    response = await get_llm_client().chat.completions.create(   # СЃР°Рј СЃРµС‚РµРІРѕР№ РІС‹Р·РѕРІ
        model=SETTINGS.model_name,        # РёРјСЏ РјРѕРґРµР»Рё РёР· РЅР°СЃС‚СЂРѕРµРє
        messages=[                        # РґРёР°Р»РѕРі РёР· РѕРґРЅРѕРіРѕ С…РѕРґР°
            {"role": "system", "content": SYSTEM_PROMPT},          # СЂРѕР»СЊ Рё РїСЂР°РІРёР»Р°
            {"role": "user",                                       # РєРѕРЅРєСЂРµС‚РЅРѕРµ Р·Р°РґР°РЅРёРµ
             "content": f"Topic: {topic}\nGenerate exactly {count} "
                        "dorks in the JSON format described above."},
        ],
        temperature=SETTINGS.temperature, # РІР°СЂРёР°С‚РёРІРЅРѕСЃС‚СЊ РіРµРЅРµСЂР°С†РёРё
    )
    content = response.choices[0].message.content           # С‚РµРєСЃС‚ РѕС‚РІРµС‚Р° РїРµСЂРІРѕРіРѕ РІР°СЂРёР°РЅС‚Р°
    if not content:                                         # РїСѓСЃС‚РѕР№ РѕС‚РІРµС‚ вЂ” РїСЂРѕР±Р»РµРјР°
        raise ValueError("РњРѕРґРµР»СЊ РІРµСЂРЅСѓР»Р° РїСѓСЃС‚РѕР№ РѕС‚РІРµС‚.")
    return parse_dorks(content.strip())                     # С‚РµРєСЃС‚ -> СЃС‚СЂСѓРєС‚СѓСЂС‹ РґР°РЅРЅС‹С…

# ----------------------------------------------------------------------------
#  Р‘Р›РћРљ 6. BACKEND-API (FastAPI): СЃС‚СЂР°РЅРёС†С‹ Рё СЌРЅРґРїРѕРёРЅС‚С‹ РґР»СЏ С„СЂРѕРЅС‚РµРЅРґР°
# ----------------------------------------------------------------------------

app = FastAPI(title="dorkAI", version="0.2.0")          # РїСЂРёР»РѕР¶РµРЅРёРµ-СЃРµСЂРІРµСЂ

class GenerateRequest(BaseModel):         # СЃС‚СЂРѕРіР°СЏ СЃС…РµРјР° РІС…РѕРґСЏС‰РµРіРѕ JSON РѕС‚ Р±СЂР°СѓР·РµСЂР°
    topic: str = Field(min_length=1, max_length=300)    # С‚РµРјР° РїРѕРёСЃРєР° (РѕР±СЏР·Р°С‚РµР»СЊРЅР°)
    count: int = Field(default=5, ge=1, le=30)          # РєРѕР»РёС‡РµСЃС‚РІРѕ РґРѕСЂРєРѕРІ 1..30

@app.get("/", response_class=HTMLResponse)              # РіР»Р°РІРЅР°СЏ СЃС‚СЂР°РЅРёС†Р° = РЅР°С€ С„СЂРѕРЅС‚РµРЅРґ
async def index() -> str:
    """РћС‚РґР°С‘С‚ РІСЃС‚СЂРѕРµРЅРЅСѓСЋ HTML-СЃС‚СЂР°РЅРёС†Сѓ РёРЅС‚РµСЂС„РµР№СЃР° (СЃРј. Р‘Р›РћРљ 8)."""
    return PAGE_HTML                                    # СЃС‚СЂРѕРєР° РѕРїСЂРµРґРµР»РµРЅР° РЅРёР¶Рµ

@app.get("/api/status")  # РїСЂРѕРІРµСЂРєР° РіРѕС‚РѕРІРЅРѕСЃС‚Рё СЃРёСЃС‚РµРјС‹
async def status() -> dict[str, Any]:
    """Р¤СЂРѕРЅС‚РµРЅРґ РІС‹Р·С‹РІР°РµС‚ СЌС‚Рѕ РїСЂРё Р·Р°РіСЂСѓР·РєРµ, С‡С‚РѕР±С‹ РїРѕРєР°Р·Р°С‚СЊ СЃС‚Р°С‚СѓСЃ РєР»СЋС‡Р°/РјРѕРґРµР»Рё."""
    return {                                            # РјРёРЅРёРјР°Р»СЊРЅС‹Р№ РѕС‚С‡С‘С‚ Рѕ СЃРѕСЃС‚РѕСЏРЅРёРё
        "api_key_set": SETTINGS.is_ready,               # Р·Р°РґР°РЅ Р»Рё API-РєР»СЋС‡
        "model": SETTINGS.model_name,                   # РєР°РєР°СЏ РјРѕРґРµР»СЊ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ
        "base_url": SETTINGS.base_url,                  # РєСѓРґР° РёРґСѓС‚ Р·Р°РїСЂРѕСЃС‹
    }

@app.post("/api/generate")
async def generate(req: GenerateRequest) -> dict[str, Any]:
    """Р“Р»Р°РІРЅС‹Р№ СЂР°Р±РѕС‡РёР№ СЌРЅРґРїРѕРёРЅС‚: С‚РµРјР° -> СЃРїРёСЃРѕРє РґРѕСЂРєРѕРІ.

    РћС€РёР±РєРё РїСЂРµРІСЂР°С‰Р°СЋС‚СЃСЏ РІ Р°РєРєСѓСЂР°С‚РЅС‹Рµ РѕС‚РІРµС‚С‹ СЃ С‡РµР»РѕРІРµС‡РµСЃРєРёРј РѕРїРёСЃР°РЅРёРµРј,
    С‡С‚РѕР±С‹ С„СЂРѕРЅС‚РµРЅРґ РјРѕРі РїРѕРєР°Р·Р°С‚СЊ РёС… РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ Р±РµР· С‚СЂРµР№СЃР±РµРєРѕРІ.
    """
    if not SETTINGS.is_ready:                           # РєР»СЋС‡ РЅРµ РІСЃС‚Р°РІР»РµРЅ РІ .env?
        return {"ok": False,                            # С„Р»Р°Рі РЅРµСѓРґР°С‡Рё РґР»СЏ С„СЂРѕРЅС‚РµРЅРґР°
                "error": "API-РєР»СЋС‡ РЅРµ Р·Р°РґР°РЅ. РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» .env СЂСЏРґРѕРј СЃРѕ СЃРєСЂРёРїС‚РѕРј "
                         "Рё РІРїРёС€РёС‚Рµ СЃС‚СЂРѕРєСѓ DORKAI_API_KEY=РІР°С€_РєР»СЋС‡."}
    clean_topic = req.topic.strip()                     # РЅРѕСЂРјР°Р»РёР·СѓРµРј РІРІРѕРґ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    if not clean_topic:                                 # РїСѓСЃС‚Р°СЏ С‚РµРјР° РїРѕСЃР»Рµ trim?
        return {"ok": False, "error": "Р’РІРµРґРёС‚Рµ С‚РµРјСѓ Р·Р°РїСЂРѕСЃР°."}
    bounded_count = max(1, min(req.count, 30))          # СЃС‚СЂР°С…РѕРІРєР° РґРёР°РїР°Р·РѕРЅР° РєРѕР»РёС‡РµСЃС‚РІР°
    try:                                                # СЃРµС‚РµРІРѕР№ РІС‹Р·РѕРІ РјРѕР¶РµС‚ РґР°С‚СЊ РјРЅРѕРіРѕ РѕС€РёР±РѕРє
        dorks = await ask_model(clean_topic, bounded_count)   # Р·Р°РїСЂРѕСЃ Рє РЅРµР№СЂРѕСЃРµС‚Рё
    except Exception as exc:                            # Р»СЋР±РѕР№ СЃР±РѕР№ СЃРµС‚Рё/РјРѕРґРµР»Рё/РїР°СЂСЃРёРЅРіР°
        return {"ok": False,                            # СЃРѕРѕР±С‰Р°РµРј РѕР± СЌС‚РѕРј РєСѓР»СЊС‚СѓСЂРЅРѕ
                "error": f"РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ РѕС‚РІРµС‚ РјРѕРґРµР»Рё: {exc}"}
    return {"ok": True,                                 # СѓСЃРїРµС…: РѕС‚РґР°С‘Рј СЂРµР·СѓР»СЊС‚Р°С‚
            "topic": clean_topic,                       # С‚РµРјР° СЌС…РѕРј
            "model": SETTINGS.model_name,               # РјРѕРґРµР»СЊ-Р°РІС‚РѕСЂ РґРѕСЂРєРѕРІ
            "dorks": dorks}                             # СЃРїРёСЃРѕРє РіРѕС‚РѕРІС‹С… РґРѕСЂРєРѕРІ

# ----------------------------------------------------------------------------
#  Р‘Р›РћРљ 7. Р—РђРџРЈРЎРљ РЎР•Р Р’Р•Р Рђ: Р°РІС‚РѕРїРѕРґСЉС‘Рј uvicorn + Р°РІС‚РѕРѕС‚РєСЂС‹С‚РёРµ Р±СЂР°СѓР·РµСЂР°
# ----------------------------------------------------------------------------

def _open_browser_later(url: str) -> None:
    """Р’ РѕС‚РґРµР»СЊРЅРѕРј РїРѕС‚РѕРєРµ Р¶РґС‘С‚ РїРѕР»С‚РѕСЂС‹ СЃРµРєСѓРЅРґС‹ Рё РѕС‚РєСЂС‹РІР°РµС‚ Р±СЂР°СѓР·РµСЂ (СЃРµСЂРІРµСЂ СѓР¶Рµ РїРѕРґРЅСЏС‚)."""
    time.sleep(1.5)                                     # РґР°С‘Рј СЃРµСЂРІРµСЂСѓ РІСЂРµРјСЏ СЃС‚Р°СЂС‚РѕРІР°С‚СЊ
    webbrowser.open(url)                                # РѕС‚РєСЂС‹РІР°РµРј СЃРёСЃС‚РµРјРЅС‹Р№ Р±СЂР°СѓР·РµСЂ

def main() -> None:
    """РўРѕС‡РєР° РІС…РѕРґР°: РїРµС‡Р°С‚СЊ РїРѕРґСЃРєР°Р·РѕРє, Р·Р°РїСѓСЃРє СЃРµСЂРІРµСЂР°, РѕС‚РєСЂС‹С‚РёРµ СЃС‚СЂР°РЅРёС†С‹."""
    for stream in (sys.stdout, sys.stderr):             # С„РёРєСЃ РєСЂР°РєРѕР·СЏР±СЂ РІ РєРѕРЅСЃРѕР»Рё Windows
        enc = getattr(stream, "encoding", "")           # С‚РµРєСѓС‰Р°СЏ РєРѕРґРёСЂРѕРІРєР° РїРѕС‚РѕРєР°
        if enc.lower() not in {"utf-8", "utf8"}:        # РµСЃР»Рё СЌС‚Рѕ РЅРµ utf-8...
            try:
                stream.reconfigure(encoding="utf-8")    # ...РїРµСЂРµРЅР°СЃС‚СЂР°РёРІР°РµРј РЅР° utf-8
            except AttributeError:                      # СЃС‚Р°СЂС‹Рµ РІРµСЂСЃРёРё Python Р±РµР· reconfigure
                pass                                    # РїСЂРѕСЃС‚Рѕ РїСЂРѕРґРѕР»Р¶Р°РµРј
    host, port = "127.0.0.1", 8765                      # Р»РѕРєР°Р»СЊРЅС‹Р№ Р°РґСЂРµСЃ: Р±РµР·РѕРїР°СЃРµРЅ Рё РїСЂРёРІР°С‚РµРЅ
    url = f"http://{host}:{port}"                       # РїРѕР»РЅР°СЏ СЃСЃС‹Р»РєР° РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    print("=" * 60)                                     # РєСЂР°СЃРёРІС‹Р№ РїСЂРёРІРµС‚СЃС‚РІРµРЅРЅС‹Р№ Р±Р»РѕРє
    print(" dorkAI вЂ” РіРµРЅРµСЂР°С‚РѕСЂ Google dorks СЃ РїРѕРјРѕС‰СЊСЋ РР")
    print(f" РРЅС‚РµСЂС„РµР№СЃ РѕС‚РєСЂС‹С‚: {url}")
    if not SETTINGS.is_ready:                           # СЃСЂР°Р·Сѓ РїСЂРµРґСѓРїСЂРµРґРёРј РїСЂРѕ РєР»СЋС‡
        print(" ! Р’РќРРњРђРќРР•: API-РєР»СЋС‡ РЅРµ Р·Р°РґР°РЅ.")
        print("   РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» .env СЂСЏРґРѕРј СЃРѕ СЃРєСЂРёРїС‚РѕРј Рё РІРїРёС€РёС‚Рµ:")
        print("   DORKAI_API_KEY=РІР°С€_РєР»СЋС‡")
    else:                                               # РІСЃС‘ РіРѕС‚РѕРІРѕ Рє СЂР°Р±РѕС‚Рµ
        print(f" РњРѕРґРµР»СЊ: {SETTINGS.model_name}")
    print(" РћСЃС‚Р°РЅРѕРІРёС‚СЊ РїСЂРѕРіСЂР°РјРјСѓ: Ctrl+C РІ СЌС‚РѕРј РѕРєРЅРµ")
    print("=" * 60)
    threading.Thread(target=_open_browser_later, args=(url,), daemon=True).start()
                                                        # Р±СЂР°СѓР·РµСЂ РѕС‚РєСЂРѕРµС‚СЃСЏ РїР°СЂР°Р»Р»РµР»СЊРЅРѕ
    import uvicorn                                      # ASGI-СЃРµСЂРІРµСЂ (РёРјРїРѕСЂС‚ Р·РґРµСЃСЊ: Р±С‹СЃС‚СЂРѕ СЃС‚Р°СЂС‚СѓРµРј)
    uvicorn.run(app, host=host, port=port, log_level="warning")  # Р±Р»РѕРєРёСЂСѓСЋС‰РёР№ Р·Р°РїСѓСЃРє СЃРµСЂРІРµСЂР°

# ============================================================================
#  Р‘Р›РћРљ 8. FRONTEND: РІСЃСЏ СЃС‚СЂР°РЅРёС†Р° РёРЅС‚РµСЂС„РµР№СЃР° вЂ” РѕРґРЅР° РІСЃС‚СЂРѕРµРЅРЅР°СЏ HTML-СЃС‚СЂРѕРєР°.
#  Vanilla JS Р±РµР· СЃР±РѕСЂРєРё, С‚С‘РјРЅР°СЏ С‚РµРјР°, РєР°СЂС‚РѕС‡РєРё РґРѕСЂРєРѕРІ, РєРЅРѕРїРєРё РєРѕРїРёСЂРѕРІР°РЅРёСЏ,
#  РїСЂСЏРјС‹Рµ СЃСЃС‹Р»РєРё РІ Google, РёРЅРґРёРєР°С‚РѕСЂ СЃС‚Р°С‚СѓСЃР° РєР»СЋС‡Р°.
# ============================================================================

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dorkAI вЂ” РіРµРЅРµСЂР°С‚РѕСЂ Google Dorks</title>
<style>
  /* ---------- Р±Р°Р·РѕРІР°СЏ С‚С‘РјРЅР°СЏ С‚РµРјР° ---------- */
  :root{
    --bg:#0d1117; --panel:#161b22; --line:#21262d;      /* С„РѕРЅ, РїР°РЅРµР»Рё, РіСЂР°РЅРёС†С‹ */
    --text:#e6edf3; --muted:#8b949e;                    /* С‚РµРєСЃС‚ РѕСЃРЅРѕРІРЅРѕР№ Рё РїСЂРёРіР»СѓС€С‘РЅРЅС‹Р№ */
    --accent:#58a6ff; --green:#3fb950; --red:#f85149;   /* Р°РєС†РµРЅС‚С‹ */
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
       font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  .wrap{max-width:900px;margin:0 auto;padding:24px 16px 64px}

  /* ---------- С€Р°РїРєР° ---------- */
  header{display:flex;align-items:center;gap:12px;margin-bottom:22px}
  .logo{font-size:26px;font-weight:700;letter-spacing:.5px}
  .logo b{color:var(--accent)}
  .badge{margin-left:auto;font-size:13px;padding:5px 11px;border-radius:999px;
         border:1px solid var(--line);background:var(--panel)}
  .badge.ok{color:var(--green)} .badge.bad{color:var(--red)}

  /* ---------- С„РѕСЂРјР° Р·Р°РїСЂРѕСЃР° ---------- */
  .card{background:var(--panel);border:1px solid var(--line);
        border-radius:14px;padding:18px;margin-bottom:20px}
  label{display:block;font-size:13px;color:var(--muted);margin:10px 0 6px}
  textarea{width:100%;min-height:72px;resize:vertical;background:#0a0d12;
           border:1px solid var(--line);border-radius:10px;color:var(--text);
           padding:12px;font-size:15px}
  textarea:focus{outline:none;border-color:var(--accent)}
  .row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:12px}
  select{background:#0a0d12;color:var(--text);border:1px solid var(--line);
         border-radius:10px;padding:10px 12px;font-size:15px}
  button{cursor:pointer;border:none;border-radius:10px;font-size:15px;
         font-weight:600;padding:11px 20px}
  .primary{background:var(--accent);color:#06121f;margin-left:auto}
  .primary:hover{filter:brightness(1.12)}
  .primary:disabled{opacity:.5;cursor:wait}

  /* ---------- СЃРѕРѕР±С‰РµРЅРёСЏ Рё СЂРµР·СѓР»СЊС‚Р°С‚С‹ ---------- */
  .msg{padding:12px 16px;border-radius:10px;margin-bottom:16px;display:none}
  .msg.err{display:block;background:rgba(248,81,73,.12);
           border:1px solid rgba(248,81,73,.45);color:var(--red)}
  .spin{display:none;color:var(--muted);margin:6px 0 0}
  .hint{font-size:12.5px;color:var(--muted);margin-top:8px;line-height:1.7}
  .hint code{background:#0a0d12;border:1px solid var(--line);
             padding:1px 6px;border-radius:6px}
  .item{background:var(--panel);border:1px solid var(--line);border-radius:12px;
        padding:14px 16px;margin-bottom:12px}
  .q{font-family:ui-monospace,Consolas,monospace;font-size:14.5px;
     color:var(--accent);word-break:break-all}
  .p{color:var(--muted);font-size:13.5px;margin-top:6px}
  .ops{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px}
  .op{font-size:11.5px;background:#0a0d12;border:1px solid var(--line);
      color:var(--muted);border-radius:999px;padding:2px 9px}
  .acts{margin-top:10px;display:flex;gap:8px}
  .mini{font-size:12.5px;font-weight:500;padding:6px 12px;background:#0a0d12;
        border:1px solid var(--line);color:var(--text)}
  .mini:hover{border-color:var(--accent)}
  .stats{color:var(--muted);font-size:13px;margin-bottom:14px}
</style>
</head>
<body>
<div class="wrap">

  <!-- ====================== РЁРђРџРљРђ РЎРўРЈРЎР« ====================== -->
  <header>
    <div class="logo">dork<b>AI</b></div>               <!-- РЅР°Р·РІР°РЅРёРµ РїСЂРѕРґСѓРєС‚Р° -->
    <div class="badge" id="status">РїСЂРѕРІРµСЂРєР°вЂ¦</div>       <!-- СЃСЋРґР° РїР°РґР°РµС‚ СЃС‚Р°С‚СѓСЃ РєР»СЋС‡Р° -->
  </header>

  <!-- ====================== Р¤РћР РњРђ Р—РђРџР РћРЎРђ ====================== -->
  <div class="card">
    <label for="topic">Р§С‚Рѕ РёС‰РµРј? РћРїРёС€РёС‚Рµ Р·Р°РґР°С‡Сѓ СЃРІРѕРёРјРё СЃР»РѕРІР°РјРё</label>
    <textarea id="topic" placeholder="РќР°РїСЂРёРјРµСЂ: Р·Р°Р±С‹С‚С‹Рµ РѕС‚РєСЂС‹С‚С‹Рµ РґРёСЂРµРєС‚РѕСЂРёРё Рё РїР°РЅРµР»Рё РІС…РѕРґР° РЅР° example.com"></textarea>

    <div class="row">
      <div>
        <label for="count">РЎРєРѕР»СЊРєРѕ РґРѕСЂРєРѕРІ</label>
        <select id="count">                              <!-- РІС‹Р±РѕСЂ РєРѕР»РёС‡РµСЃС‚РІР° 1..30 -->
          <option>5</option><option selected>10</option><option>15</option>
          <option>20</option><option>25</option><option>30</option>
        </select>
      </div>
      <button class="primary" id="go">РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ</button>   <!-- РєРЅРѕРїРєР° Р·Р°РїСѓСЃРєР° -->
    </div>

    <div class="hint">                                   <!-- РїРѕРґСЃРєР°Р·РєР° РЅРѕРІРёС‡РєСѓ РїСЂРѕ .env -->
      РќСѓР¶РµРЅ API-РєР»СЋС‡? РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» <code>.env</code> СЂСЏРґРѕРј СЃРѕ СЃРєСЂРёРїС‚РѕРј:<br>
      <code>DORKAI_API_KEY=РІР°С€_РєР»СЋС‡</code> &nbsp;вЂ” Рё РїРµСЂРµР·Р°РїСѓСЃС‚РёС‚Рµ РїСЂРѕРіСЂР°РјРјСѓ.
    </div>
  </div>

  <div class="msg err" id="err"></div>                   <!-- РєРѕРЅС‚РµР№РЅРµСЂ РѕС€РёР±РѕРє -->
  <div class="spin" id="spin">РР РґСѓРјР°РµС‚ РЅР°Рґ Р·Р°РїСЂРѕСЃРѕРјвЂ¦ РѕР±С‹С‡РЅРѕ 5вЂ“25 СЃРµРєСѓРЅРґ.</div>

  <div class="stats" id="stats"></div>                   <!-- СЃС‚СЂРѕРєР° "РјРѕРґРµР»СЊ/РєРѕР»-РІРѕ" -->
  <div id="results"></div>                               <!-- СЃСЋРґР° СЂРµРЅРґРµСЂСЏС‚СЃСЏ РєР°СЂС‚РѕС‡РєРё -->
</div>

<script>
"use strict";
/* ---------- РІСЃРїРѕРјРѕРіР°С‚РµР»СЊРЅС‹Рµ СЃСЃС‹Р»РєРё РЅР° СЌР»РµРјРµРЅС‚С‹ DOM ---------- */
const $ = (id) => document.getElementById(id);           // РєРѕСЂРѕС‚РєРёР№ Р°Р»РёР°СЃ РїРѕР»СѓС‡РµРЅРёСЏ
const topicEl=$("topic"), countEl=$("count"), goBtn=$("go");
const errEl=$("err"), spinEl=$("spin"), resEl=$("results"), statsEl=$("stats");

/* ---------- СЌРєСЂР°РЅРёСЂРѕРІР°РЅРёРµ: РІС‹РІРѕРґРёРј С‚РµРєСЃС‚ РјРѕРґРµР»Рё Р±РµР·РѕРїР°СЃРЅРѕ ---------- */
const esc = (s) => String(s ?? "")
  .replaceAll("&","&amp;").replaceAll("<","&lt;")
  .replaceAll(">","&gt;").replaceAll('"',"&quot;");      // Р·Р°С‰РёС‚Р° РѕС‚ XSS-РёРЅСЉРµРєС†РёР№

/* ---------- РїСЂРѕРІРµСЂРєР° СЃС‚Р°С‚СѓСЃР° РєР»СЋС‡Р° РїСЂРё Р·Р°РіСЂСѓР·РєРµ СЃС‚СЂР°РЅРёС†С‹ ---------- */
fetch("/api/status").then(r=>r.json()).then(st=>{
  const b=$("status");                                   // Р±РµР№РґР¶ РІ С€Р°РїРєРµ
  if(st.api_key_set){                                    // РєР»СЋС‡ РЅР°Р№РґРµРЅ вЂ” Р·РµР»С‘РЅС‹Р№ СЃС‚Р°С‚СѓСЃ
    b.className="badge ok"; b.textContent="РєР»СЋС‡ РїРѕРґРєР»СЋС‡С‘РЅ В· "+st.model;
  }else{                                                 // РєР»СЋС‡Р° РЅРµС‚ вЂ” РєСЂР°СЃРЅС‹Р№ СЃС‚Р°С‚СѓСЃ
    b.className="badge bad"; b.textContent="API-РєР»СЋС‡ РЅРµ Р·Р°РґР°РЅ";
  }
}).catch(()=>{ $("status").textContent="СЃРµСЂРІРµСЂ РЅРµРґРѕСЃС‚СѓРїРµРЅ"; });

/* ---------- РіР»Р°РІРЅС‹Р№ РѕР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё В«РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊВ» ---------- */
goBtn.addEventListener("click", async ()=>{
  const topic = topicEl.value.trim();                    // С‚РµРєСЃС‚ С‚РµРјС‹ РѕС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
  errEl.className="msg"; resEl.innerHTML=""; statsEl.textContent="";
  if(!topic){                                            // РїСѓСЃС‚РѕР№ РІРІРѕРґ вЂ” РїСЂРµРґСѓРїСЂРµРґРёРј
    errEl.textContent="Р’РІРµРґРёС‚Рµ С‚РµРјСѓ Р·Р°РїСЂРѕСЃР°.";
    errEl.className="msg err"; return;
  }
  goBtn.disabled=true; spinEl.style.display="block";     // РІРєР»СЋС‡Р°РµРј СЃРїРёРЅРЅРµСЂ
  try{
    const resp = await fetch("/api/generate",{           // РѕС‚РїСЂР°РІР»СЏРµРј Р·Р°РґР°С‡Сѓ Р±СЌРєРµРЅРґСѓ
      method:"POST",
      headers:{ "Content-Type":"application/json" },    // С‚РµР»Рѕ вЂ” JSON
      body: JSON.stringify({ topic: topic, count:+countEl.value }),
    });
    const data = await resp.json();                      // СЂР°Р·Р±РёСЂР°РµРј РѕС‚РІРµС‚ СЃРµСЂРІРµСЂР°
    if(!data.ok){                                        // СЃРµСЂРІРµСЂ СЃРѕРѕР±С‰РёР» РѕР± РѕС€РёР±РєРµ
      showError(data.error || "РќРµРёР·РІРµСЃС‚РЅР°СЏ РѕС€РёР±РєР°."); return;
    }
    render(data);                                        // СЂРёСЃСѓРµРј РєР°СЂС‚РѕС‡РєРё СЂРµР·СѓР»СЊС‚Р°С‚Р°
  }catch(e){                                             // СЃРµС‚СЊ РѕС‚РІР°Р»РёР»Р°СЃСЊ Рё С‚.Рї.
    showError("РќРµС‚ СЃРІСЏР·Рё СЃ СЃРµСЂРІРµСЂРѕРј: "+e.message);
  }finally{
    goBtn.disabled=false; spinEl.style.display="none";   // РІРѕР·РІСЂР°С‰Р°РµРј РєРЅРѕРїРєСѓ
  }
});

function showError(text){                                // РїРѕРєР°Р·Р°С‚СЊ СЃРѕРѕР±С‰РµРЅРёРµ РѕР± РѕС€РёР±РєРµ
  errEl.textContent=text; errEl.className="msg err";
}

/* ---------- РѕС‚СЂРёСЃРѕРІРєР° СЃРїРёСЃРєР° РґРѕСЂРєРѕРІ ---------- */
function render(data){
  statsEl.textContent = "РњРѕРґРµР»СЊ: "+data.model+" В· РїРѕР»СѓС‡РµРЅРѕ РґРѕСЂРєРѕРІ: "+data.dorks.length
    +" В· С‚РµРјР°: "+data.topic;
  data.dorks.forEach((d,i)=>{
    const ops=(d.operators||[]).map(o=>'<span class="op">'+esc(o)+"</span>").join("");
    const card=document.createElement("div");            // РєР°СЂС‚РѕС‡РєР° РѕРґРЅРѕРіРѕ РґРѕСЂРєР°
    card.className="item";
    card.innerHTML =
      '<div class="q">'+(i+1)+'. '+esc(d.query)+"</div>"+
      (d.purpose ? '<div class="p">'+esc(d.purpose)+"</div>" : "")+
      (ops ? '<div class="ops">'+ops+"</div>" : "")+
      '<div class="acts">'+
        '<button class="mini act-copy">РљРѕРїРёСЂРѕРІР°С‚СЊ</button>'+
        '<button class="mini act-open">РћС‚РєСЂС‹С‚СЊ РІ Google</button>'+
      "</div>";
    card.querySelector(".act-copy").onclick=()=>navigator.clipboard.writeText(d.query);
    card.querySelector(".act-open").onclick=()=>window.open(
      "https://www.google.com/search?q="+encodeURIComponent(d.query),"_blank");
    resEl.appendChild(card);                             // РґРѕР±Р°РІР»СЏРµРј РІ РѕР±С‰РёР№ СЃРїРёСЃРѕРє
  });
}
</script>
</body>
</html>
"""

# ----------------------------------------------------------------------------
#  РўРћР§РљРђ Р’РҐРћР”Рђ вЂ” РѕР±СЏР·Р°С‚РµР»СЊРЅРѕ РџРћРЎР›Р• РѕРїСЂРµРґРµР»РµРЅРёСЏ PAGE_HTML (СЃРј. РєРѕРјРјРµРЅС‚Р°СЂРёР№ РІС‹С€Рµ).
# ----------------------------------------------------------------------------

if __name__ == "__main__":                              # Р·Р°С‰РёС‚Р° РѕС‚ РёРјРїРѕСЂС‚Р° РєР°Рє РјРѕРґСѓР»СЏ
    main()                                              # СЃС‚Р°СЂС‚ РїСЂРѕРіСЂР°РјРјС‹
