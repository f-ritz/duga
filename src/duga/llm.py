"""LLM interaction using DeepSeek via the official OpenAI-compatible endpoint.

Model to use by default: deepseek-v4-flash (fast & cheap).
You can override via DEEPSEEK_MODEL env if desired.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

from openai import OpenAI

from .config import get_env, load_env

log = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek-v4-flash"
BASE_URL = "https://api.deepseek.com"


def get_client() -> OpenAI:
    load_env()
    api_key = get_env("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set. Add it to .env")

    return OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
    )


def build_system_prompt(user_style_prompt: str, recent_briefings_text: str = "") -> str:
    """Construct the system message.

    We keep the user prompt.txt as the dominant style instruction.
    We also add a short "how to use history" rule.
    """
    base = (
        "You are writing a daily briefing based on fresh web, website, and social data.\n"
        "Follow the user's style instructions exactly.\n\n"
        "USER STYLE INSTRUCTIONS:\n"
        f"{user_style_prompt}\n\n"
    )
    if recent_briefings_text.strip():
        base += (
            "RECENT BRIEFINGS (last 14 days) - use these ONLY to note continuity, "
            "follow-ups, or changes since the previous briefing. "
            "Do NOT copy large sections verbatim.\n"
            f"{recent_briefings_text}\n\n"
        )
    base += (
        "OUTPUT RULES:\n"
        "- Produce only the briefing content. No meta commentary.\n"
        "- Use markdown.\n"
        "- Be factual and cite sources.\n"
    )
    return base


def build_user_message(collected_text: str) -> str:
    return (
        "Here is all the raw intelligence collected today. "
        "Synthesize it into a daily briefing following the instructions.\n\n"
        "=== RAW DATA START ===\n"
        f"{collected_text}\n"
        "=== RAW DATA END ===\n"
    )


def generate_briefing(
    user_style_prompt: str,
    collected_text: str,
    recent_briefings_text: str = "",
    model: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call DeepSeek and return the generated briefing text."""
    client = get_client()
    model = model or get_env("DEEPSEEK_MODEL") or DEFAULT_MODEL
    input_len = len(collected_text) + len(user_style_prompt) + len(recent_briefings_text)
    log.info(f"Calling LLM generate ({model}) input~{input_len} chars")

    messages = [
        {
            "role": "system",
            "content": build_system_prompt(user_style_prompt, recent_briefings_text),
        },
        {
            "role": "user",
            "content": build_user_message(collected_text),
        },
    ]

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.4,   # slightly creative but factual
    )

    content = resp.choices[0].message.content or ""
    return content.strip()


def build_synthesis_system_prompt(user_style_prompt: str, recent_briefings_text: str = "") -> str:
    """System prompt specifically for merging chunked briefings into one final output."""
    base = (
        "You are synthesizing a daily briefing from multiple smaller briefings.\n"
        "Each smaller briefing was generated from a chunk of ~10 targets (keywords, websites, or social handles).\n"
        "Follow the user's style instructions exactly.\n\n"
        "USER STYLE INSTRUCTIONS:\n"
        f"{user_style_prompt}\n\n"
    )
    if recent_briefings_text.strip():
        base += (
            "RECENT BRIEFINGS (last 14 days) - use only for continuity and change detection. "
            "Do NOT copy large sections.\n"
            f"{recent_briefings_text}\n\n"
        )
    base += (
        "SYNTHESIS RULES:\n"
        "- Combine the chunk briefings into ONE coherent, concise daily briefing.\n"
        "- Eliminate duplicate information; keep the strongest version of each story.\n"
        "- Prioritize high-signal items across all chunks.\n"
        "- Preserve factual tone and source citations where available.\n"
        "- Produce ONLY the final briefing content. No meta commentary about chunks.\n"
        "- Use markdown headings and bullets as appropriate per the style.\n"
    )
    return base


def synthesize_briefings(
    user_style_prompt: str,
    chunked_briefings_text: str,
    recent_briefings_text: str = "",
    model: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call the LLM to merge several chunk briefings into a single final daily briefing."""
    client = get_client()
    model = model or get_env("DEEPSEEK_MODEL") or DEFAULT_MODEL
    input_len = len(chunked_briefings_text) + len(user_style_prompt) + len(recent_briefings_text)
    log.info(f"Calling LLM synthesize ({model}) from chunks, input~{input_len} chars")

    messages = [
        {
            "role": "system",
            "content": build_synthesis_system_prompt(user_style_prompt, recent_briefings_text),
        },
        {
            "role": "user",
            "content": (
                "Below are briefings produced from separate chunks of today's targets.\n"
                "Synthesize them into one final daily briefing following the instructions.\n\n"
                "=== CHUNK BRIEFINGS START ===\n"
                f"{chunked_briefings_text}\n"
                "=== CHUNK BRIEFINGS END ===\n"
            ),
        },
    ]

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.4,
    )
    content = resp.choices[0].message.content or ""
    return content.strip()


# --- Optional vision support (images) ---
# DeepSeek vision support is evolving. The code below tries the OpenAI image_url format.
# If it fails for your account/region, the function returns a short textual description
# or you can point VISION_* env vars at another compatible provider.

def analyze_images(image_urls: list[str], context: str = "") -> list[dict[str, str]]:
    """Attempt to get short descriptions of images/reels using the LLM vision endpoint (DeepSeek or VISION_* override).

    Supports IG post images, reels (via videoUrl or thumbnail), carousels.
    Descriptions are later inserted into the briefing data.
    Falls back gracefully if vision not available.
    """
    if not image_urls:
        return []

    client = get_client()
    model = get_env("VISION_MODEL") or get_env("DEEPSEEK_MODEL") or DEFAULT_MODEL

    results = []
    log.info(f"Analyzing {len(image_urls)} media item(s) with vision model {model}")
    for url in image_urls[: int(get_env("MAX_IMAGES_TO_ANALYZE", "5") or 5)]:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Describe this image, reel thumbnail, or visual content briefly and factually. Focus on key elements, text, people, actions, context if obvious. Context from post: {context[:300]}"},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                ],
                max_tokens=300,
            )
            desc = resp.choices[0].message.content or ""
            results.append({"url": url, "description": desc.strip()})
            log.debug(f"Vision desc for {url[:60]}...: {desc[:100]}...")
        except Exception as e:
            # Vision probably not enabled or different model needed. Common for some DeepSeek setups.
            msg = f"[vision unavailable for this media] ({e})"
            results.append({"url": url, "description": msg})
            log.warning(f"Vision analysis failed for {url}: {e}")
    log.info(f"Vision analysis complete: {len(results)} descriptions")
    return results
