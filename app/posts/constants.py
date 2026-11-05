from typing import Dict, List

CATEGORIES: List[Dict[str, str]] = [
    {
        "slug": "travel-stories",
        "name": "Travel Stories",
        "description": "Journeys, detours and the people met along the way.",
    },
    {
        "slug": "photography",
        "name": "Photography",
        "description": "Photographs only. A place name on each photo is optional.",
    },
    {
        "slug": "food",
        "name": "Food",
        "description": "Street stalls, kitchens and recipes from everywhere.",
    },
    {
        "slug": "culture",
        "name": "Culture",
        "description": "Traditions, festivals, art and history.",
    },
    {
        "slug": "adventure",
        "name": "Adventure",
        "description": "Peaks, trails, waves and everything outdoors.",
    },
    {
        "slug": "lifestyle",
        "name": "Lifestyle",
        "description": "Everyday rituals, homes and slow living.",
    },
    {
        "slug": "tech",
        "name": "Tech",
        "description": "Gear, tools and notes from the digital road.",
    },
    {
        "slug": "art",
        "name": "Art",
        "description": "Paintings, sketches, crafts and creative work from the road.",
    },
    {
        "slug": "other",
        "name": "Other",
        "description": "Everything that doesn't fit a box.",
    },
]

CATEGORY_SLUGS = {c["slug"] for c in CATEGORIES}
PHOTOGRAPHY_SLUG = "photography"
