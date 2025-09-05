# Zoning is decentralized; we use links + LLM summarization when a code URL is configured.
# For now, we return placeholder URLs based on municipality name for eCode360 search patterns.
from typing import Optional, Dict

def guess_zoning_links(municipality_name: str) -> Dict[str, str]:
    name = (municipality_name or "").strip().replace(" ", "+")
    return {
        "general_search": f"https://www.google.com/search?q={name}+zoning+map+solar+energy+ecode360",
        "ecode360_library": "https://www.generalcode.com/library/"
    }

def summarize_code_text(text: str) -> str:
    # Placeholder for LLM call; summarize if provided
    if not text:
        return ""
    return text[:800] + ("..." if len(text) > 800 else "")
