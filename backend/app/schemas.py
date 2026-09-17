from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AuthInput(Schema):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    name: str = Field(default="", max_length=160)


class CareerEntry(Schema):
    title: str = Field(max_length=240)
    organization: str = Field(default="", max_length=240)
    description: str = Field(default="", max_length=6000)
    start: str = Field(default="", max_length=10)
    end: str = Field(default="", max_length=10)
    url: str = Field(default="", max_length=2000)


class DNA(Schema):
    @field_validator(
        "desired_roles",
        "acceptable_roles",
        "interests",
        "target_companies",
        "sectors",
        "languages",
        mode="after",
    )
    @classmethod
    def clean_lists(cls, values):
        return list(dict.fromkeys(v.strip()[:240] for v in values if v.strip()))

    name: str = Field(default="", max_length=160)
    headline: str = Field(default="", max_length=240)
    summary: str = Field(default="", max_length=8000)
    location: str = Field(default="", max_length=240)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=80)
    github: str = Field(default="", max_length=2000)
    linkedin: str = Field(default="", max_length=2000)
    portfolio: str = Field(default="", max_length=2000)
    desired_roles: list[str] = Field(default_factory=list, max_length=40)
    acceptable_roles: list[str] = Field(default_factory=list, max_length=40)
    seniority: str = "unknown"
    work_models: list[Literal["remote", "hybrid", "onsite"]] = Field(default_factory=list)
    relocation: bool = False
    salary_min: float | None = Field(default=None, ge=0)
    salary_currency: str = "BRL"
    salary_period: Literal["month", "year", "hour"] = "month"
    experience_months: int | None = Field(default=None, ge=0, le=960)
    education_level: int | None = Field(default=None, ge=0, le=5)
    interests: list[str] = Field(default_factory=list, max_length=40)
    target_companies: list[str] = Field(default_factory=list, max_length=80)
    sectors: list[str] = Field(default_factory=list, max_length=40)
    goals: str = Field(default="", max_length=4000)
    languages: list[str] = Field(default_factory=list, max_length=30)
    experiences: list[CareerEntry] = Field(default_factory=list, max_length=60)
    education: list[CareerEntry] = Field(default_factory=list, max_length=40)
    certifications: list[CareerEntry] = Field(default_factory=list, max_length=60)
    projects: list[CareerEntry] = Field(default_factory=list, max_length=80)
    ai_consent: bool = False
    follow_up_days: int = Field(default=7, ge=1, le=90)
    follow_up_enabled: bool = True


class ProfileUpdate(Schema):
    data: DNA
    version: int = Field(ge=1)


class SkillInput(Schema):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="technical", max_length=120)
    level: int = Field(default=1, ge=1, le=5)
    months: int | None = Field(default=None, ge=0, le=960)
    last_used: str | None = Field(default=None, max_length=10)
    developing: bool = False


class EvidenceInput(Schema):
    kind: Literal["experience", "project", "education", "certification", "course", "github"]
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=10, max_length=6000)
    url: str | None = Field(default=None, max_length=2000)
    confidence: float = Field(default=1, ge=0, le=1)


class Requirement(Schema):
    skill: str = Field(min_length=1, max_length=120)
    mandatory: bool = True
    description: str = Field(default="", max_length=2000)


class JobData(Schema):
    title: str = Field(min_length=1, max_length=240)
    company: str = Field(min_length=1, max_length=240)
    location: str = Field(default="", max_length=240)
    description: str = Field(min_length=20, max_length=60000)
    url: str | None = Field(default=None, max_length=2000)
    source: str = Field(default="manual", max_length=100)
    external_id: str | None = Field(default=None, max_length=160)
    work_model: Literal["remote", "hybrid", "onsite", "unknown"] = "unknown"
    seniority: Literal["intern", "junior", "mid", "senior", "lead", "unknown"] = "unknown"
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    salary_currency: str = Field(default="BRL", max_length=10)
    salary_period: Literal["month", "year", "hour"] = "month"
    experience_months: int | None = Field(default=None, ge=0, le=960)
    education_level: int | None = Field(default=None, ge=0, le=5)
    requirements: list[Requirement] = Field(default_factory=list, max_length=100)
    responsibilities: list[str] = Field(default_factory=list, max_length=80)
    soft_skills: list[str] = Field(default_factory=list, max_length=40)
    benefits: list[str] = Field(default_factory=list, max_length=60)
    languages: list[str] = Field(default_factory=list, max_length=30)
    keywords: list[str] = Field(default_factory=list, max_length=60)
    published_at: str | None = None
    deadline: str | None = None

    @model_validator(mode="after")
    def salary_range(self):
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("Salário máximo deve ser maior que o mínimo")
        return self


class ParseInput(Schema):
    text: str = Field(min_length=20, max_length=60000)


class UrlInput(Schema):
    url: str = Field(min_length=8, max_length=2000)


class StatusInput(Schema):
    status: str = Field(max_length=50)
    version: int = Field(ge=1)
    rejection_reason: str | None = Field(default=None, max_length=3000)


class TextInput(Schema):
    body: str = Field(min_length=1, max_length=12000)


class ContactInput(Schema):
    name: str = Field(min_length=1, max_length=240)
    email: EmailStr | None = None
    url: str | None = Field(default=None, max_length=2000)
    role: str = Field(default="", max_length=240)


class UtcSchema(Schema):
    @field_validator("*", mode="after")
    @classmethod
    def utc_datetime(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("Informe data e hora com fuso horário")
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


class FollowUpInput(UtcSchema):
    due_at: datetime


class InterviewInput(UtcSchema):
    title: str = Field(min_length=1, max_length=240)
    scheduled_at: datetime
    kind: Literal["hr", "technical", "case", "final"] = "hr"
    notes: str = Field(default="", max_length=8000)


class InterviewUpdate(Schema):
    feedback: str = Field(default="", max_length=12000)
    notes: str = Field(default="", max_length=8000)
    checklist: list[str] = Field(default_factory=list, max_length=30)


class MessageInput(Schema):
    kind: Literal[
        "first_contact",
        "linkedin",
        "email",
        "application",
        "follow_up",
        "thanks",
        "reply",
        "interest",
        "update",
    ]
    instructions: str = Field(default="", max_length=3000)


class CoachInput(Schema):
    body: str = Field(min_length=1, max_length=6000)
    conversation_id: str | None = None
    job_id: str | None = None


class SourceInput(Schema):
    provider: Literal["greenhouse", "lever"]
    board: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")


class DocumentInput(Schema):
    name: str = Field(min_length=1, max_length=240)
    kind: Literal["resume", "cover_letter", "note"] = "note"
    text: str = Field(min_length=1, max_length=60000)
    parent_id: str | None = None
