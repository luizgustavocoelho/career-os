"""Deterministic, versioned score. Unknown information is excluded, never treated as a match."""

import hashlib
import json

from app.domain.skills import normalize

VERSION = "1.0.0"
WEIGHTS = {
    "technical": 24,
    "experience": 12,
    "education": 6,
    "career_goal": 12,
    "location": 6,
    "work_model": 6,
    "salary": 6,
    "evidence": 16,
    "skill_gap": 6,
    "seniority": 6,
}
SENIORITY = {"intern": 0, "junior": 1, "mid": 2, "senior": 3, "lead": 4}


def calculate(dna: dict, skills: list[dict], job: dict) -> dict:
    components = []
    requirements = []
    by_name = {normalize(s["name"]): s for s in skills}
    seen = set()
    for req in job.get("requirements", []):
        key = normalize(req["skill"])
        if key in seen:
            continue
        seen.add(key)
        skill = by_name.get(key)
        evidence = [e for e in (skill or {}).get("evidence", []) if e.get("confidence", 0) >= 0.5]
        strength = 0 if not skill else (0.4 if skill.get("developing") else 0.7)
        if evidence and skill and not skill.get("developing"):
            strength = 1
        requirements.append(
            {
                **req,
                "normalized": key,
                "status": "met" if strength == 1 else "partial" if strength else "missing",
                "strength": strength,
                "evidence": evidence,
                "explanation": "Evidência registrada; não é certificação de domínio."
                if evidence
                else "Habilidade declarada, sem evidência suficiente."
                if skill
                else "Não registrada no perfil.",
            }
        )

    def add(name, value, explanation):
        components.append(
            {
                "name": name,
                "score": None if value is None else round(max(0, min(100, value)), 1),
                "weight": WEIGHTS[name],
                "explanation": explanation,
            }
        )

    total = sum(2 if r["mandatory"] else 1 for r in requirements)
    tech = sum(r["strength"] * (2 if r["mandatory"] else 1) for r in requirements)
    add(
        "technical",
        100 * tech / total if total else None,
        "Obrigatórios pesam 2; desejáveis pesam 1. Declaração = 70%, em desenvolvimento = 40%, com evidência = 100%.",
    )
    for name, field in (("experience", "experience_months"), ("education", "education_level")):
        actual, needed = dna.get(field), job.get(field)
        add(
            name,
            None
            if actual is None or needed is None
            else 100
            if needed == 0
            else 100 * actual / needed,
            "Comparação com a exigência explícita; experiência não é inferida de palavras-chave."
            if name == "experience"
            else "Comparação do nível de formação informado (0–5).",
        )
    title = normalize(job["title"])
    desired = [normalize(x) for x in dna.get("desired_roles", [])]
    acceptable = [normalize(x) for x in dna.get("acceptable_roles", [])]

    def title_matches(roles):
        return any(set(role.split()).issubset(set(title.split())) for role in roles if role)

    add(
        "career_goal",
        None
        if not desired and not acceptable
        else 100
        if title_matches(desired)
        else 75
        if title_matches(acceptable)
        else 20,
        "Alinhamento com cargos desejados ou aceitáveis informados pelo candidato; revise títulos equivalentes.",
    )
    location, local = normalize(job.get("location", "")), normalize(dna.get("location", ""))
    add(
        "location",
        None
        if not location or not local
        else 100
        if dna.get("relocation") or location == local
        else 25,
        "Localidade declarada ou disponibilidade para mudança. Remoto não implica elegibilidade geográfica.",
    )
    mode = job.get("work_model", "unknown")
    add(
        "work_model",
        None
        if mode == "unknown" or not dna.get("work_models")
        else 100
        if mode in dna["work_models"]
        else 0,
        "Modelo da vaga versus preferências do perfil.",
    )
    salary, minimum = job.get("salary_max") or job.get("salary_min"), dna.get("salary_min")
    comparable = all(dna.get(k) == job.get(k) for k in ("salary_currency", "salary_period"))
    add(
        "salary",
        None
        if salary is None or minimum is None or not comparable
        else 100
        if minimum == 0
        else 100 * salary / minimum,
        "Comparação somente entre mesma moeda e período; sem conversão presumida.",
    )
    add(
        "evidence",
        100 * sum(bool(r["evidence"]) * (2 if r["mandatory"] else 1) for r in requirements) / total
        if total
        else None,
        "Cobertura dos requisitos por evidências registradas, sem inferir proficiência avançada.",
    )
    mandatory = [r for r in requirements if r["mandatory"]]
    add(
        "skill_gap",
        100 * sum(r["status"] != "missing" for r in mandatory) / len(mandatory)
        if mandatory
        else None,
        "Cobertura declarada dos requisitos obrigatórios; lacunas são exibidas individualmente.",
    )
    actual, needed = SENIORITY.get(dna.get("seniority")), SENIORITY.get(job.get("seniority"))
    add(
        "seniority",
        None if actual is None or needed is None else 100 - abs(actual - needed) * 30,
        "Distância entre níveis de senioridade declarados; não presume anos de experiência.",
    )
    known = [c for c in components if c["score"] is not None]
    coverage = sum(c["weight"] for c in known)
    score = round(sum(c["score"] * c["weight"] for c in known) / coverage, 1) if coverage else 0
    blockers = [r["skill"] for r in mandatory if r["status"] == "missing"]
    classification = (
        "high" if score >= 80 else "worth" if score >= 60 else "review" if score >= 40 else "low"
    )
    if coverage < 50 or not requirements:
        classification = "review"
    elif blockers and classification == "high":
        classification = "worth"
    return {
        "score": score,
        "classification": classification,
        "coverage": coverage,
        "components": components,
        "requirements": requirements,
        "blockers": blockers,
        "reason": f"{score}% nos componentes conhecidos; cobertura de informação de {coverage}%. "
        + (
            f"{len(blockers)} requisito(s) obrigatório(s) sem habilidade registrada."
            if blockers
            else "Revise as evidências e exigências antes de decidir."
        ),
        "algorithm": VERSION,
        "input_hash": hashlib.sha256(
            json.dumps([dna, skills, job, VERSION], sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
    }
