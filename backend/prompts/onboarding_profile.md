You are building a personalized newspaper profile for a reader.

Reader self-description:
"{{description}}"

Return JSON with this shape ONLY:
{
  "topics": ["world", "pakistan", "technology"],
  "weights": {"world": 1.0, "pakistan": 0.8},
  "tone": "neutral",
  "outside_bubble_ratio": 0.15
}

Rules:
- topics must be drawn from the Topic enum.
- weights are 0.0–1.0.
- outside_bubble_ratio is 0.0–0.5.
- No prose, no markdown fences.
