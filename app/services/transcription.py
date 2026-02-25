"""Transcription refinement and enhancement services."""

from typing import Optional

from ..clients import groq_client
from ..config import ENHANCEMENT_MODEL, REFINED_TRANSLATION_MODEL


async def enhance_transcript(title: str, raw_transcript: str) -> Optional[str]:
    """Use Groq to refine the transcript."""
    if not groq_client:
        return None
    prompt = f"""
Role: You are a Technical Transcript Editor specializing in Machine Learning and Computer Science lectures.

Raw Transcript: {raw_transcript}


Content Guidelines:
- Generate your response in markdown format. All headings MUST be bold and caps (e.g ** HEADING **).
- All headings MUST be followed by a horizontal line break (e.g ***) on the next line.
- SUMMARIZE the transcript provided into easily absorbable overviews of each mentioned topic.
- Preserve original semantic meaning — do NOT add new facts or remove essential content.
- Fix phonetic/translation errors using context and the lecture title to disambiguate technical terms.
- Repair sentence structure and improve readability while keeping the instructional/lecture tone.


"""


    try:
        response = groq_client.chat.completions.create(
            model=ENHANCEMENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception as e:
        print(f"Enhancement error: {e}")
        return None


def refine_urdu_transcript(
    raw_urdu_text: str,
    previous_chunks: Optional[list[str]] = None
) -> Optional[str]:
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
        "If previous Urdu context is provided, use it only to disambiguate terms and resolve pronouns for the current input. "
        "Do not translate the context separately; only translate the current input.\n\n"
        "If you receieve an input of english rather than urdu, or a mix between the two, still return your response in english following the instructions given."
        "Output: Return ONLY the refined English translation. DON'T add any commentary or add introductions such as 'Sure, here is the required translation: '."

    )

    cleaned_context = [chunk.strip() for chunk in (previous_chunks or []) if chunk and chunk.strip()]
    if cleaned_context:
        context_lines = "\n".join(
            f"{index + 1}. {chunk}" for index, chunk in enumerate(cleaned_context)
        )
        user_prompt = (
            "Previous Urdu Context (chronological):\n"
            f"{context_lines}\n\n"
            "Current Urdu Input:\n"
            f"{raw_urdu_text}"
        )
    else:
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
