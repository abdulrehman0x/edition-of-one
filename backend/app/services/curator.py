# backend/app/services/curator.py
from typing import Dict, Any, List

def curate_edition_for_profile(profile: dict, date_str: str) -> dict:
    learned_weights = profile.get("learned_weights", {})
    
    # Curated articles with multi-topic metadata
    articles = [
        {
            "title": "Pakistan government advances major tax and subsidy reform initiative",
            "summary": "The ministry of finance has announced updated fiscal guidelines aimed at stabilizing national inflation reserves and boosting IT sector exports.",
            "source_name": "Dawn News",
            "source_url": "https://www.dawn.com",
            "topics": ["business", "pakistan", "economy"]
        },
        {
            "title": "Global AI chipmakers announce next-generation open architecture",
            "summary": "Major semiconductor vendors have unveiled open-source hardware specifications designed to accelerate localized LLM inference engines.",
            "source_name": "TechCrunch",
            "source_url": "https://techcrunch.com",
            "topics": ["technology", "ai", "hardware"]
        },
        {
            "title": "Pakistan vs England test series ends in high-stakes draw at Lahore",
            "summary": "A resolute final wicket partnership secured a thrilling draw on the fifth day, leaving the three-match test series tied.",
            "source_name": "ESPNcricinfo",
            "source_url": "https://www.espncricinfo.com",
            "topics": ["sports", "cricket", "pakistan"]
        },
        {
            "title": "Clean energy investments hit record high across Asian markets",
            "summary": "Renewable infrastructure funding has outpaced traditional grid expansions across major regional economies this quarter.",
            "source_name": "BBC World News",
            "source_url": "https://www.bbc.com/news",
            "topics": ["world", "energy", "business"]
        }
    ]
    
    # Score articles dynamically based on learned user preference weights
    scored_articles = []
    for art in articles:
        score = 1.0
        topics = art.get("topics", ["general"])
        
        for topic in topics:
            multiplier = learned_weights.get(topic.lower(), 1.0)
            score *= multiplier
            
        scored_articles.append((score, art))
        
    # Sort articles so highest-scored (learned favorites) appear first as lead stories
    scored_articles.sort(key=lambda x: x[0], reverse=True)
    sorted_arts = [art for score, art in scored_articles]
    
    lead = sorted_arts[0] if sorted_arts else None
    secondaries = sorted_arts[1:4] if len(sorted_arts) >= 4 else sorted_arts[1:]

    return {
        "date": date_str,
        "edition_id": f"ed-{date_str}",
        "lead_story": lead,
        "secondary_stories": secondaries,
        "weather": {"city": "Islamabad", "temp_c": 25.6, "condition": "Clear"}
    }