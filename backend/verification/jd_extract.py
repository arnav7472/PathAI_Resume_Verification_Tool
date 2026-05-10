from __future__ import annotations

from ..evidence.text import contains_phrase, split_sentences
from .knowledge import ACTION_VERBS, DOMAIN_TERMS, SKILL_ALIASES


def extract_job_requirements(job_description: str) -> dict[str, object]:
    jd = job_description or ""
    skills: dict[str, None] = {}
    for skill, aliases in SKILL_ALIASES.items():
        for sentence in split_sentences(jd):
            if any(contains_phrase(sentence, alias) for alias in aliases):
                skills[skill] = None
                break
    action_verbs: list[str] = []
    for verb in ACTION_VERBS:
        if any(contains_phrase(sentence, verb) for sentence in split_sentences(jd)):
            action_verbs.append(verb)

    domains = [
        domain
        for domain, terms in DOMAIN_TERMS.items()
        if any(contains_phrase(jd, term) for term in terms)
    ]
    certifications = [
        skill for skill in skills if "Certified" in skill or skill in {"Security+", "CISSP"}
    ]
    required_keywords = sorted({*skills.keys(), *domains, *certifications})
    return {
        "skills": list(skills.keys()),
        "action_verbs": action_verbs,
        "domains": domains,
        "certifications": certifications,
        "keywords": required_keywords,
    }
