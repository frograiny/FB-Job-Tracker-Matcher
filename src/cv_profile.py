import re
from dataclasses import dataclass


SKILL_KEYWORDS = [
    "python", "fastapi", "flask", "django", "pytorch", "tensorflow", "keras",
    "scikit-learn", "opencv", "u-net", "bi-lstm", "react", "typescript",
    "javascript", "sql", "docker", "docker compose", "git", "linux", "go",
    "c#", "c++", "rest api", "gemini api", "llm", "prompt engineering",
    "agentic workflows", "machine learning", "deep learning", "computer vision",
    "nlp", "security", "waf", "vulnerability scanner", "system architecture",
]

ROLE_SIGNALS = {
    "AI / Machine Learning Intern": [
        "machine learning", "deep learning", "pytorch", "tensorflow", "keras",
        "scikit-learn", "computer vision", "opencv", "u-net", "bi-lstm",
    ],
    "Python Backend Intern": [
        "python", "fastapi", "flask", "django", "sql", "rest api", "docker",
    ],
    "AI Agent / LLM Intern": [
        "llm", "gemini api", "prompt engineering", "agentic workflows",
        "google antigravity sdk", "structured markdown outputs",
    ],
    "Security / WAF Intern": [
        "security", "waf", "vulnerability scanner", "sqli", "xss", "csrf",
        "path traversal", "command injection",
    ],
    "Full-stack Intern": [
        "react", "typescript", "javascript", "fastapi", "flask", "sql", "docker",
    ],
}

LOCATION_KEYWORDS = ["hà nội", "ha noi", "hanoi", "tp.hcm", "hồ chí minh", "remote", "hybrid"]


@dataclass(frozen=True)
class CvProfile:
    skills: list[str]
    target_roles: list[str]
    locations: list[str]
    search_queries: list[str]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_cv_profile(cv_text: str, max_roles: int = 4) -> CvProfile:
    """Extract practical search signals from a user's CV text."""
    normalized = normalize_text(cv_text)
    skills = [skill for skill in SKILL_KEYWORDS if skill in normalized]
    locations = [location for location in LOCATION_KEYWORDS if location in normalized]

    role_scores: list[tuple[str, int]] = []
    for role, keywords in ROLE_SIGNALS.items():
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score:
            role_scores.append((role, score))

    role_scores.sort(key=lambda item: item[1], reverse=True)
    target_roles = [role for role, _ in role_scores[:max_roles]]
    search_queries = build_search_queries(target_roles, skills)

    return CvProfile(
        skills=skills,
        target_roles=target_roles,
        locations=locations,
        search_queries=search_queries,
    )


def build_search_queries(target_roles: list[str], skills: list[str], limit: int = 8) -> list[str]:
    """Build Facebook-search-friendly recruitment queries from CV signals."""
    queries: list[str] = []
    for role in target_roles:
        normalized_role = role.replace(" / ", " ").replace("Intern", "intern")
        queries.append(f"tuyển dụng {normalized_role}")
        queries.append(f"{normalized_role} internship")

    for skill in skills[:6]:
        queries.append(f"tuyển dụng {skill} intern")

    deduped: list[str] = []
    seen = set()
    for query in queries:
        key = query.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(query)
    return deduped[:limit]


def score_text_against_profile(text: str, profile: CvProfile) -> int:
    """Return a simple 0-100 relevance score between a job text and CV profile."""
    normalized = normalize_text(text)
    skill_hits = sum(1 for skill in profile.skills if skill in normalized)
    role_hits = sum(1 for role in profile.target_roles if normalize_text(role.replace("/", " ")) in normalized)
    location_hits = sum(1 for location in profile.locations if location in normalized)

    raw_score = skill_hits * 12 + role_hits * 20 + location_hits * 5
    return min(100, raw_score)


def summarize_profile(profile: CvProfile) -> str:
    return (
        f"Target roles: {', '.join(profile.target_roles) or 'N/A'}\n"
        f"Skills: {', '.join(profile.skills[:12]) or 'N/A'}\n"
        f"Locations: {', '.join(profile.locations) or 'N/A'}\n"
        f"Search queries: {', '.join(profile.search_queries) or 'N/A'}"
    )
