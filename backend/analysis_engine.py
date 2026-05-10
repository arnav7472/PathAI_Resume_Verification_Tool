from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass


ACTION_VERBS = [
    "achieved",
    "analyzed",
    "architected",
    "automated",
    "built",
    "collaborated",
    "configured",
    "created",
    "decreased",
    "delivered",
    "deployed",
    "designed",
    "developed",
    "engineered",
    "implemented",
    "improved",
    "increased",
    "led",
    "maintained",
    "managed",
    "migrated",
    "monitored",
    "optimized",
    "reduced",
    "secured",
    "shipped",
    "streamlined",
    "tested",
]

BUZZWORDS = [
    "expert",
    "guru",
    "ninja",
    "rockstar",
    "passionate",
    "world class",
    "cutting edge",
    "thought leader",
    "proficient",
]

SKILL_ALIASES: dict[str, list[str]] = {
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "Python": ["python", "py"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "c sharp"],
    "Go": ["golang", "go"],
    "Rust": ["rust"],
    "SQL": ["sql", "postgresql", "postgres", "mysql", "sqlite"],
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node.js", "nodejs", "node"],
    "Express": ["express", "express.js"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring boot"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform"],
    "Jenkins": ["jenkins"],
    "GitHub Actions": ["github actions"],
    "GitLab CI": ["gitlab ci"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure", "microsoft azure"],
    "Google Cloud": ["gcp", "google cloud"],
    "AWS EKS": ["eks", "aws eks"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Kafka": ["kafka", "apache kafka"],
    "Linux": ["linux", "ubuntu", "debian", "red hat", "rhel"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch", "torch"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "LangChain": ["langchain"],
    "OpenAI": ["openai", "gpt", "chatgpt"],
    "NLP": ["nlp", "natural language processing"],
    "OCR": ["ocr", "optical character recognition"],
    "Nmap": ["nmap"],
    "Burp Suite": ["burp suite", "burp"],
    "Wireshark": ["wireshark"],
    "Metasploit": ["metasploit"],
    "SIEM": ["siem", "splunk", "sentinel"],
    "REST APIs": ["rest api", "rest apis", "restful api", "rest"],
    "GraphQL": ["graphql"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration"],
    "Agile": ["agile", "scrum"],
    "AWS Certified": ["aws certified", "aws certification"],
    "Azure Certified": ["azure certified", "azure certification"],
    "Security+": ["security+", "comptia security"],
    "CISSP": ["cissp"],
}

DOMAIN_TERMS = {
    "cloud": ["cloud", "aws", "azure", "gcp", "serverless", "eks", "ec2", "s3"],
    "devops": ["devops", "ci/cd", "docker", "kubernetes", "terraform", "jenkins"],
    "security": ["security", "cybersecurity", "siem", "nmap", "burp", "wireshark", "vulnerability"],
    "ai/ml": ["ai", "ml", "machine learning", "deep learning", "tensorflow", "pytorch", "langchain"],
    "backend": ["api", "backend", "database", "microservices", "node", "fastapi", "express"],
    "frontend": ["frontend", "react", "typescript", "ui", "web"],
}

STRICTNESS = {
    "low": {"min_evidence": 1, "missing_penalty": 20, "inflated_penalty": 8, "weak_threshold": 45},
    "medium": {"min_evidence": 1, "missing_penalty": 30, "inflated_penalty": 14, "weak_threshold": 55},
    "high": {"min_evidence": 2, "missing_penalty": 42, "inflated_penalty": 24, "weak_threshold": 70},
}


@dataclass
class SkillHit:
    skill: str
    count: int
    evidence: list[str]


def normalize_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if not compact:
        return []
    pieces = re.split(r"(?<=[.!?])\s+|(?:\s*[•*]\s*)|\n+", compact)
    return [piece.strip(" -–—\t") for piece in pieces if len(piece.strip()) > 2]


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase).replace(r"\ ", r"[\s\-/]+")
    return re.compile(rf"(?<![a-z0-9+#]){escaped}(?![a-z0-9+#])", re.IGNORECASE)


def _contains(text: str, phrase: str) -> bool:
    return bool(_phrase_pattern(phrase).search(text))


def extract_action_verbs(text: str) -> list[str]:
    found = OrderedDict()
    for verb in ACTION_VERBS:
        if _contains(text, verb):
            found[verb] = None
    return list(found.keys())


def extract_skills(text: str) -> dict[str, SkillHit]:
    sentences = split_sentences(text)
    hits: dict[str, SkillHit] = {}
    for skill, aliases in SKILL_ALIASES.items():
        evidence: list[str] = []
        count = 0
        for sentence in sentences:
            matched = any(_contains(sentence, alias) for alias in aliases)
            if matched:
                count += 1
                if len(evidence) < 4:
                    evidence.append(sentence)
        if count:
            hits[skill] = SkillHit(skill=skill, count=count, evidence=evidence)
    return hits


def extract_years(text: str) -> int | None:
    patterns = [
        r"\b(\d{1,2})\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)\b",
        r"\b(?:experience|exp)\s*:?\s*(\d{1,2})\s*\+?\s*years?\b",
    ]
    values: list[int] = []
    for pattern in patterns:
        values.extend(int(match) for match in re.findall(pattern, text, flags=re.IGNORECASE))
    return max(values) if values else None


def extract_timeline(text: str) -> list[dict[str, object]]:
    timeline: list[dict[str, object]] = []
    for sentence in split_sentences(text):
        for match in re.finditer(
            r"\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current)\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            end_raw = match.group(2).lower()
            timeline.append(
                {
                    "start_year": int(match.group(1)),
                    "end_year": "present" if end_raw in {"present", "current"} else int(end_raw),
                    "evidence": sentence,
                }
            )
    return timeline


def extract_job_requirements(job_description: str) -> dict[str, object]:
    jd = normalize_text(job_description)
    skills = extract_skills(jd)
    action_verbs = extract_action_verbs(jd)
    domains = [
        domain
        for domain, terms in DOMAIN_TERMS.items()
        if any(_contains(jd, term) for term in terms)
    ]
    certifications = [
        skill for skill in skills if "Certified" in skill or skill in {"Security+", "CISSP"}
    ]
    required_keywords = sorted(set(skills.keys()) | set(domains) | set(certifications))
    return {
        "skills": list(skills.keys()),
        "action_verbs": action_verbs,
        "domains": domains,
        "certifications": certifications,
        "keywords": required_keywords,
    }


def _claim_status(confidence: int, evidence_count: int, has_buzzword: bool, strictness: str) -> str:
    min_evidence = STRICTNESS[strictness]["min_evidence"]
    if has_buzzword and evidence_count < min_evidence:
        return "buzzword"
    if evidence_count >= min_evidence and confidence >= 72:
        return "verified"
    if confidence < STRICTNESS[strictness]["weak_threshold"]:
        return "inflated"
    return "likely"


def _confidence_for_claim(evidence_count: int, has_action: bool, has_metric: bool, has_buzzword: bool, strictness: str) -> int:
    score = 42 + min(evidence_count, 4) * 16
    if has_action:
        score += 14
    if has_metric:
        score += 10
    if has_buzzword:
        score -= STRICTNESS[strictness]["inflated_penalty"]
    if strictness == "low":
        score += 8
    elif strictness == "high" and evidence_count < 2 and not has_action:
        score -= 12
    return max(5, min(98, round(score)))


def _skill_claims(skills: dict[str, SkillHit], strictness: str) -> list[dict[str, object]]:
    claims: list[dict[str, object]] = []
    for skill, hit in skills.items():
        evidence_text = " ".join(hit.evidence)
        has_action = bool(extract_action_verbs(evidence_text))
        has_metric = bool(re.search(r"\b\d+%|\b\d+x|\b\d+\s*(users|requests|projects|teams|servers)\b", evidence_text, re.I))
        has_buzzword = any(_contains(evidence_text, word) for word in BUZZWORDS)
        confidence = _confidence_for_claim(hit.count, has_action, has_metric, has_buzzword, strictness)
        status = _claim_status(confidence, hit.count, has_buzzword, strictness)
        claims.append(
            {
                "type": "skill",
                "value": skill,
                "claim": f"{skill} experience",
                "evidence": hit.evidence,
                "supporting_evidence": hit.evidence[0] if hit.evidence else "",
                "confidence": confidence,
                "status": status,
                "evidence_count": hit.count,
            }
        )
    return claims


def _pattern_claims(text: str, strictness: str) -> list[dict[str, object]]:
    claims: list[dict[str, object]] = []
    sentences = split_sentences(text)
    patterns = [
        ("experience", r"\b\d{1,2}\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)\b"),
        ("achievement", r"\b(?:improved|increased|reduced|decreased|optimized|cut)\b[^.?!]*\b\d+%"),
        ("project", r"\b(?:built|developed|created|designed|implemented|deployed|managed)\b[^.?!]*(?:api|application|platform|pipeline|cluster|model|project|system)s?\b"),
        ("leadership", r"\b(?:led|managed|mentored|collaborated|coordinated)\b[^.?!]*(?:team|engineers|developers|stakeholders|project)s?\b"),
        ("certification", r"\b(?:certified|certification|aws certified|azure certified|security\+|cissp)\b"),
    ]
    seen: set[str] = set()
    for sentence in sentences:
        for claim_type, pattern in patterns:
            if not re.search(pattern, sentence, flags=re.IGNORECASE):
                continue
            value = sentence[:140]
            key = f"{claim_type}:{value.lower()}"
            if key in seen:
                continue
            seen.add(key)
            has_buzzword = any(_contains(sentence, word) for word in BUZZWORDS)
            confidence = _confidence_for_claim(1, bool(extract_action_verbs(sentence)), bool(re.search(r"\d", sentence)), has_buzzword, strictness)
            claims.append(
                {
                    "type": claim_type,
                    "value": value,
                    "claim": value,
                    "evidence": [sentence],
                    "supporting_evidence": sentence,
                    "confidence": confidence,
                    "status": _claim_status(confidence, 1, has_buzzword, strictness),
                    "evidence_count": 1,
                }
            )
    return claims


def analyze_resume(
    resume_text: str,
    job_description: str = "",
    strictness: str = "medium",
    cross_reference_sync: bool = True,
) -> dict[str, object]:
    strictness = strictness.lower() if strictness.lower() in STRICTNESS else "medium"
    text = normalize_text(resume_text)
    jd = normalize_text(job_description)
    resume_skills = extract_skills(text)
    jd_requirements = extract_job_requirements(jd)
    action_verbs = extract_action_verbs(text)
    claims = _skill_claims(resume_skills, strictness) + _pattern_claims(text, strictness)

    required_skills = set(jd_requirements["skills"]) if jd else set()
    matched_skills = sorted(required_skills & set(resume_skills.keys()))
    missing_skills = sorted(required_skills - set(resume_skills.keys()))
    resume_skill_count = max(1, len(resume_skills))
    match_ratio = len(matched_skills) / max(1, len(required_skills)) if required_skills else min(1.0, len(resume_skills) / 8)
    coverage_bonus = min(18, resume_skill_count * 2)
    compatibility = round(max(0, min(100, (match_ratio * 76) + coverage_bonus)))

    inflated_claims = [claim for claim in claims if claim["status"] in {"inflated", "buzzword"}]
    verified_claims = [claim for claim in claims if claim["status"] == "verified"]
    weak_areas = []
    if missing_skills:
        weak_areas.append(f"Missing JD skills: {', '.join(missing_skills[:8])}")
    if not action_verbs:
        weak_areas.append("Resume lacks strong action verbs.")
    if inflated_claims:
        weak_areas.append(f"{len(inflated_claims)} claim(s) have weak evidence.")

    findings: list[dict[str, str]] = []
    if missing_skills:
        findings.append({"message": f"Resume is missing {len(missing_skills)} job description requirement(s).", "severity": "medium"})
    if not action_verbs:
        findings.append({"message": "No strong action verbs were detected in the resume text.", "severity": "medium"})
    else:
        findings.append({"message": f"Detected action verbs: {', '.join(action_verbs[:12])}.", "severity": "low"})

    consistency_findings: list[dict[str, object]] = []
    if cross_reference_sync:
        sentences = split_sentences(text)
        for skill, hit in resume_skills.items():
            skill_only = hit.count == 1 and any(re.search(r"\bskills?\b|technologies\b", s, re.I) for s in hit.evidence)
            if skill_only:
                consistency_findings.append(
                    {
                        "claim": f"{skill} listed but not supported in work/project evidence",
                        "status": "inflated",
                        "evidence": hit.evidence,
                    }
                )
        for sentence in sentences:
            if any(_contains(sentence, word) for word in BUZZWORDS) and not extract_action_verbs(sentence):
                consistency_findings.append({"claim": sentence[:120], "status": "buzzword", "evidence": [sentence]})

    risk_score = 100 - compatibility
    risk_score += len(inflated_claims) * STRICTNESS[strictness]["inflated_penalty"]
    risk_score += len(missing_skills) * (STRICTNESS[strictness]["missing_penalty"] / 10)
    if not action_verbs:
        risk_score += 16 if strictness == "high" else 10
    if cross_reference_sync:
        risk_score += min(24, len(consistency_findings) * (8 if strictness == "high" else 5))
    risk_score = round(max(0, min(100, risk_score)))
    confidence = round(max(0, min(100, (compatibility * 0.78) + (len(verified_claims) * 3) + (len(action_verbs) * 1.5) - (len(inflated_claims) * 5))))

    if not findings:
        findings.append({"message": "No major heuristic contradictions detected.", "severity": "low"})
    for item in consistency_findings[:6]:
        findings.append({"message": str(item["claim"]), "severity": "high" if item["status"] == "inflated" else "medium"})

    evidence_map = [
        {
            "claim": claim["claim"],
            "type": claim["type"],
            "status": claim["status"],
            "confidence": claim["confidence"],
            "evidence": claim["evidence"],
            "warning": "" if claim["status"] in {"verified", "likely"} else "Weak or generic evidence only.",
        }
        for claim in claims
    ]

    return {
        "skills": sorted(resume_skills.keys()),
        "skill_counts": {skill: hit.count for skill, hit in resume_skills.items()},
        "action_verbs": action_verbs,
        "claims": claims,
        "evidence": evidence_map,
        "timeline": extract_timeline(text),
        "job_description": jd,
        "job_requirements": jd_requirements,
        "compatibility_score": compatibility,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "weak_areas": weak_areas,
        "risk_score": risk_score,
        "confidence": confidence,
        "findings": findings,
        "consistency_findings": consistency_findings,
        "strictness": strictness,
        "cross_reference_sync": cross_reference_sync,
        "years_experience": extract_years(text),
        "text": text,
    }
