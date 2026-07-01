"""
Builds the prompt sent to the LLM for story generation, combining the
text of selected source articles with user-supplied parameters
(topic, title, length, tone, audience).
"""

from __future__ import annotations
import sqlite3


def build_prompt(
    articles: list[sqlite3.Row],
    topic: str | None = None,
    title: str | None = None,
    length_words: int = 400,
    tone: str | None = None,
    audience: str | None = None,
    angle: str | None = None,
) -> str:
    """
    Construct a single prompt string combining source material and
    generation instructions. Articles are included with clear separators
    and source attribution so the model can ground claims and the user
    can later verify against the originals.
    """
    source_block_parts = []
    for i, article in enumerate(articles, start=1):
        source_block_parts.append(
            f"--- SOURCE {i}: {article['title']} "
            f"(via {article['source_name']}, {article['url']}) ---\n"
            f"{article['text']}\n"
        )
    source_block = "\n".join(source_block_parts)

    instructions = ["Write a news article based on the source material below."]

    if topic:
        instructions.append(f"Topic focus: {topic}.")
    if title:
        instructions.append(f"Use this exact headline: \"{title}\".")
    else:
        instructions.append("Write an appropriate headline for the article.")
    if angle:
        instructions.append(f"Angle / emphasis: {angle}.")
    if tone:
        instructions.append(f"Tone: {tone}.")
    if audience:
        instructions.append(f"Target audience: {audience}.")

    instructions.append(f"Target length: approximately {length_words} words.")
    instructions.append(
        "Synthesize the source material into original prose -- do not copy "
        "sentences verbatim from the sources. Attribute specific claims to "
        "their source where natural (e.g. 'according to [Source Name]')."
    )
    instructions.append(
        "Only use information present in the source material below. Do not "
        "invent facts, quotes, statistics, or details not found in the sources."
    )

    instruction_block = "\n".join(f"- {line}" for line in instructions)

    prompt = (
        f"INSTRUCTIONS:\n{instruction_block}\n\n"
        f"SOURCE MATERIAL:\n{source_block}\n\n"
        f"Now write the article."
    )
    return prompt
