import pytest
from pydantic import ValidationError

from app.ai.provider import Advice, ResumeExtraction
from app.domain.parsers import extract_skills, local_job, local_resume, pdf_text
from app.domain.scoring import calculate
from app.domain.skills import canonical_url, fingerprint, normalize
from app.schemas import JobData
from tests.conftest import pdf_fixture


@pytest.mark.parametrize(
    "raw,expected",
    [
        (" PYTHON 3 ", "python"),
        ("Postgres", "postgresql"),
        ("Comunicação", "comunicacao"),
        ("Amazon Web Services", "aws"),
        ("C++", "c++"),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_score_deterministic_and_evidence(vacancy):
    dna = {
        "desired_roles": ["Engenheiro de Dados"],
        "work_models": ["remote"],
        "seniority": "junior",
    }
    skill = {"name": "Python", "evidence": [], "developing": False}
    first = calculate(dna, [skill], vacancy)
    assert first == calculate(dna, [skill], vacancy)
    assert first["requirements"][0]["status"] == "partial"
    assert first["blockers"] == ["SQL"]
    skill["evidence"] = [{"id": "e1", "confidence": 1, "title": "Pipeline comprovado"}]
    second = calculate(dna, [skill], vacancy)
    assert second["score"] > first["score"]
    assert second["requirements"][0]["status"] == "met"
    assert 0 <= first["score"] <= 100


def test_unknown_is_not_perfect():
    result = calculate({}, [], {"title": "Vaga", "requirements": []})
    assert result["score"] == 0
    assert result["coverage"] == 0
    assert result["classification"] == "review"
    assert all(c["score"] is None for c in result["components"])


def test_salary_different_currency_excluded(vacancy):
    result = calculate(
        {"salary_min": 5000, "salary_currency": "BRL", "salary_period": "month"},
        [],
        {**vacancy, "salary_max": 6000, "salary_currency": "USD", "salary_period": "month"},
    )
    assert next(c for c in result["components"] if c["name"] == "salary")["score"] is None


def test_low_coverage_not_high_priority():
    result = calculate({"work_models": ["remote"]}, [], {"title": "Vaga", "work_model": "remote"})
    assert result["score"] == 100
    assert result["coverage"] == 6
    assert result["classification"] == "review"


def test_normalized_duplicate_requirements(vacancy):
    vacancy["requirements"] += [{"skill": "Python 3", "mandatory": True}]
    assert len(calculate({}, [], vacancy)["requirements"]) == 3


def test_dedupe_fingerprint_and_url(vacancy):
    assert fingerprint(vacancy) == fingerprint({**vacancy, "company": "  EMPRESA DE TESTE "})
    assert (
        canonical_url("https://example.com/jobs/1/?utm_source=test&role=2#x")
        == "https://example.com/jobs/1?role=2"
    )


def test_parsers_and_pdf():
    assert extract_skills("Usamos Python 3 e PostgreSQL; parte do projeto em TypeScript.") == [
        "postgresql",
        "python",
        "typescript",
    ]
    parsed = local_job("Python obrigatório.\nAWS é um diferencial.")
    assert not next(r for r in parsed.requirements if r.skill == "aws").mandatory
    assert "Test Candidate" in pdf_text(pdf_fixture())
    extracted = local_resume(pdf_text(pdf_fixture()))
    assert extracted["profile"]["email"] == "candidate@example.com"
    assert extracted["warnings"]
    paragraph = local_job("Python é obrigatório. AWS é um diferencial.")
    assert next(r for r in paragraph.requirements if r.skill == "python").mandatory
    assert not next(r for r in paragraph.requirements if r.skill == "aws").mandatory


def test_contracts_reject_invalid_output(vacancy):
    with pytest.raises(ValidationError):
        JobData.model_validate({**vacancy, "salary_min": 10000, "salary_max": 100})
    with pytest.raises(ValidationError):
        Advice.model_validate({"body": "Uma resposta", "citations": [{"invented": "source"}]})
    with pytest.raises(ValidationError):
        ResumeExtraction.model_validate(
            {"profile": {"imagined_experience": 10}, "skills": [], "warnings": []}
        )
    assert JobData.model_json_schema()["additionalProperties"] is False
