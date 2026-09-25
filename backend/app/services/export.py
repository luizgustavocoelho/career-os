"""Owner-scoped, explicit export allowlist. No authentication material."""

import json
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select

from app import models as m
from app.serializers import serialize

EXPORTS = {
    "profile": m.Profile,
    "skills": m.ProfileSkill,
    "evidences": m.Evidence,
    "jobs": m.Job,
    "applications": m.Application,
    "timeline": m.ApplicationEvent,
    "notes": m.Note,
    "interviews": m.Interview,
    "followups": m.FollowUp,
    "conversations": m.AIConversation,
    "messages": m.AIMessage,
    "contacts": m.Contact,
    "drafts": m.MessageDraft,
    "analyses": m.MatchAnalysis,
    "components": m.MatchComponent,
    "requirements": m.JobRequirement,
    "sources": m.JobSource,
    "saved_searches": m.SavedJobSearch,
    "documents": m.Document,
}


def export_zip(db, user):
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        counts = {}
        for name, model in EXPORTS.items():
            rows = db.scalars(select(model).where(model.user_id == user.id)).all()
            counts[name] = len(rows)
            archive.writestr(
                name + ".json",
                json.dumps([serialize(row) for row in rows], ensure_ascii=False, indent=2),
            )
            if model is m.Document:
                for row in rows:
                    archive.writestr(
                        f"documents/{row.id}.pdf" if row.content else f"documents/{row.id}.txt",
                        row.content if row.content else row.text.encode("utf-8"),
                    )
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "format": "careeros-export-v1",
                    "created_at": m.now().isoformat() + "Z",
                    "account": {"name": user.name, "email": user.email},
                    "counts": counts,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    return output.getvalue()
