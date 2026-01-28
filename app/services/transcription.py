"""Transcription refinement and enhancement services."""

from typing import Optional
import httpx

from ..clients import groq_client, openrouter_api_key
from ..config import ENHANCEMENT_MODEL, REFINED_TRANSLATION_MODEL


async def enhance_transcript(title: str, raw_transcript: str) -> Optional[str]:
    """Use OpenRouter to refine the transcript."""
    if not openrouter_api_key:
        return None
    prompt = (
        "Role: You are a Technical Transcript Editor specializing in Machine Learning and Computer Science lectures.\n"
        "Task: Your goal is to take a raw, machine-translated transcript from an Urdu-to-English system and "
        "\"reconstruct\" it into a professional, readable English transcript.\n\n"
        f"Title: {title}\n"
        f"Raw Transcript: {raw_transcript}\n\n"
        "Guidelines for Refinement:\n"
        "- Preserve Semantic Meaning: Do not add new information or remove existing concepts. The goal is to make the existing content coherent.\n"
        "- Fix \"Phonetic\" and Translation Errors: Machine translations often misinterpret technical terms (e.g., \"Wright Next\" usually means \"Right, next,\" and \"linear length\" might mean \"linear regression\"). Use the Title to make educated guesses for these technical corrections.\n"
        "- Repair Sentence Structure: Convert disjointed, repetitive phrases into smooth, grammatically correct English. (e.g., \"on the basis of the rules, the machine has taken out the rules\" $\\rightarrow$ \"Based on these rules, the machine has extracted patterns...\").\n"
        "- Maintain Lecture Tone: Keep the instructional and conversational feel, but remove unnecessary fillers or extreme redundancies that don't add value.\n\n"
        "Formatting:\n"
        "- Use Paragraphs to separate distinct ideas.\n"
        "- Use Bold for key technical terms.\n"
        "- Use LaTeX for any mathematical formulas (e.g., $y = wx + b$).\n\n"
        "Output Format: Return only the refined transcript. If a specific section is completely nonsensical even with context, place the best-guess interpretation in [brackets]."
    )

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Live Urdu Transcriber"
    }

    payload = {
        "model": ENHANCEMENT_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2000
    }

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip() if content else None
    except Exception as e:
        print(f"Enhancement error: {e}")
        return None


def refine_urdu_transcript(raw_urdu_text: str) -> Optional[str]:
    """Use Groq LLM to translate Urdu transcript into refined English."""
    if not groq_client:
        return None

    system_prompt = (
        "You are an expert Urdu-to-English interpreter specializing in technical discourse. "
        "You will receive a raw transcription in Urdu. Your goal is to provide a fluent, grammatically correct English translation.\n\n"
        "The Context: The speaker is discussing [e.g., Data Science and Data Mining].\n\n"
        "Your Tasks:\n\n"
        "Literal vs. Intentional: If the raw text contains \"nonsensical\" phrases or poor grammar, "
        "infer the speaker's intent based on the surrounding technical context.\n\n"
        "Smoothing: Fix run-on sentences and ensure the flow sounds like a professional lecture or discussion.\n\n"
        "If you receieve an input of english rather than urdu, or a mix between the two, still return your response in english following the instructions given."
        "Output: Return ONLY the refined English translation. DON'T add any commentary or add introductions such as 'Sure, here is the required translation: '."
    )

    user_prompt = f"Input (Urdu Transcription): {raw_urdu_text}"

    try:
        response = groq_client.chat.completions.create(
            model=REFINED_TRANSLATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1200
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception as e:
        print(f"Refined translation error: {e}")
        return None
