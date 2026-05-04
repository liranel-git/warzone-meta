"""
Claude-powered classifier that reads scraped content,
extracts weapon builds, and assigns tier ratings.
Uses tool_use for structured output and prompt caching
to keep the long system prompt cheap across batches.
"""

import os
import json
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an expert Call of Duty: Warzone (Black Ops 7 / WZBO7) weapon meta analyst. You have deep knowledge of the current season's meta in Warzone Black Ops 7.

IMPORTANT: Only extract builds for weapons that exist in Warzone Black Ops 7 (WZBO7). Ignore any builds from previous Warzone integrations (e.g. MW2, MW3, BO6 exclusive weapons) if they are no longer in the current WZBO7 loot pool.

Your job:
1. Read community content (Reddit posts, YouTube transcripts/descriptions) about WZBO7.
2. Extract specific weapon builds — each build needs a weapon name AND its attachment list.
3. Assign each build a tier based on community sentiment, vote counts, and expert creator opinion.

Tier definitions (be strict — not everything is meta):
- Absolute Meta: The weapon everyone is running. Dominates lobbies. Potentially broken. The undisputed #1 pick in its class.
- Meta: Excellent. Competitive in all situations. A top 3–5 weapon overall. You will not be punished for running this.
- A: Solid. Viable and competitive. Not broken but holds its own. A good player choice.
- B: Below average. Has clear weaknesses vs Meta options. Situational at best.
- F: Avoid entirely. Outclassed, recently nerfed to irrelevance, or a pure gimmick.

When extracting builds you MUST capture:
- weapon_name: Exact weapon (e.g., "MCW", "RAM-7", "Holger 26", "MTZ-762")
- weapon_class: AR / SMG / LMG / Sniper / Shotgun / Marksman / Pistol / Melee
- tier: Exactly one of "Absolute Meta", "Meta", "A", "B", "F"
- attachments: List of attachment strings in slot:value format when possible (e.g., "Muzzle: Quartermaster", "Barrel: Dozer-90 Long Barrel"). If slot is unclear just list the attachment name.
- confidence: 0.0–1.0. Use high confidence (0.85+) only when multiple sources agree or a top creator explicitly says it's meta.
- reasoning: 1–2 sentences. What evidence from the content supports this tier?

Skip any build with fewer than 3 attachments mentioned — it's incomplete.
Do not invent attachments not mentioned in the source content.
"""

CLASSIFY_TOOL = {
    "name": "record_weapon_builds",
    "description": "Record the weapon builds extracted from community content with their tier classifications",
    "input_schema": {
        "type": "object",
        "properties": {
            "builds": {
                "type": "array",
                "description": "All weapon builds found in the provided content",
                "items": {
                    "type": "object",
                    "properties": {
                        "weapon_name":  {"type": "string"},
                        "weapon_class": {
                            "type": "string",
                            "enum": ["AR", "SMG", "LMG", "Sniper", "Shotgun", "Marksman", "Pistol", "Melee"],
                        },
                        "tier": {
                            "type": "string",
                            "enum": ["Absolute Meta", "Meta", "A", "B", "F"],
                        },
                        "attachments": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "reasoning":   {"type": "string"},
                    },
                    "required": ["weapon_name", "weapon_class", "tier", "attachments", "confidence", "reasoning"],
                },
            }
        },
        "required": ["builds"],
    },
}


def _format_items(items: list[dict]) -> str:
    parts = []
    for i, item in enumerate(items, 1):
        upvotes = f" | {item['upvotes']} upvotes" if item.get("upvotes") else ""
        parts.append(
            f"=== Source {i} [{item['source_type'].upper()}{upvotes}] ===\n"
            f"Title: {item['title']}\n"
            f"URL: {item.get('source_url', 'N/A')}\n\n"
            f"{item['text']}\n"
        )
    return "\n".join(parts)


def classify(items: list[dict]) -> list[dict]:
    """
    items: list of scraped content dicts from reddit.py / youtube.py
    returns: list of build dicts ready for database.upsert_build
    """
    if not items:
        return []

    formatted = _format_items(items)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # cache the long system prompt
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Analyze the following {len(items)} pieces of community content "
                    f"and extract all weapon builds you find:\n\n{formatted}"
                ),
            }
        ],
        tools=[CLASSIFY_TOOL],
        tool_choice={"type": "any"},
    )

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_weapon_builds":
            raw_builds = block.input.get("builds", [])
            # Annotate each build with the source info from the first matching item
            # (best effort — Claude picks the most representative source)
            enriched = []
            for b in raw_builds:
                # Find the highest-upvote source to credit
                best = max(items, key=lambda x: x.get("upvotes", 0))
                enriched.append({
                    **b,
                    "source_type":  best["source_type"],
                    "source_url":   best.get("source_url", ""),
                    "source_title": best["title"],
                    "upvotes":      best.get("upvotes", 0),
                })
            return enriched

    print("[classifier] no tool_use block in response")
    return []


def classify_in_batches(items: list[dict], batch_size: int = 8) -> list[dict]:
    """Classify in batches to avoid hitting context limits."""
    all_builds = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        print(f"[classifier] processing batch {i // batch_size + 1} ({len(batch)} items)")
        builds = classify(batch)
        all_builds.extend(builds)
    return all_builds
