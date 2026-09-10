from dataclasses import dataclass


@dataclass
class SafetyCheckResult:
    passed: bool
    reasons: list[str]


_HYPE_TERMS_JA = [
    "絶対",
    "必ず",
    "100%",
    "確実",
    "確定",
    "最高",
    "最強",
    "最良",
    "一番",
    "唯一",
    "奇跡",
    "革命",
]

_HYPE_TERMS_EN = [
    "absolutely",
    "guaranteed",
    "100%",
    "definitely",
    "best",
    "only",
    "miracle",
    "revolutionary",
    "amazing",
    "incredible",
    "proven",
    "forever",
]


def hype_terms_for_language(language: str) -> list[str]:
    if language == "ja":
        return list(_HYPE_TERMS_JA)
    elif language == "en":
        return list(_HYPE_TERMS_EN)
    else:
        raise ValueError(f"unsupported language: {language}")


def check_copy_safety(
    product_name: str,
    title: str,
    description: str,
    disclosure_tag: str,
    hype_terms: list[str],
) -> SafetyCheckResult:
    """
    Checks copy safety:
    1. Presence of disclosure tag (#PR or #affiliate)
    2. No hype/exaggeration terms
    3. Product name appears in title or description

    Note: Image review is performed by Claude Code agent side (see DAILY_RUN_PROMPT.md).
    """
    reasons: list[str] = []
    combined = f"{title}\n{description}"
    combined_lower = combined.lower()

    if disclosure_tag.lower() not in combined_lower:
        reasons.append(f"missing disclosure tag: {disclosure_tag}")

    for term in hype_terms:
        if term.lower() in combined_lower:
            reasons.append(f"contains hype/exaggeration term: {term}")

    keywords = [w for w in product_name.split() if len(w) > 1]
    if keywords and not any(k.lower() in combined_lower for k in keywords):
        reasons.append(
            "link-content mismatch: generated copy not mention product name"
        )

    return SafetyCheckResult(passed=not reasons, reasons=reasons)
