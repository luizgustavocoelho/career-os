"""Local administrative commands; requires filesystem/database administrator access."""

import argparse
import getpass
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import delete, select

from app.config import settings
from app.db import SessionLocal
from app.models import SessionToken, User
from app.security import hasher


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    reset = sub.add_parser("reset-password")
    reset.add_argument("email")
    backup = sub.add_parser("backup-sqlite")
    backup.add_argument("destination")
    sub.add_parser("ai-smoke")
    sub.add_parser("check-migrations")
    migrate = sub.add_parser("migrate-sqlite-to-postgres")
    migrate.add_argument("source", help="Arquivo SQLite local; faça backup antes.")
    migrate.add_argument(
        "--target-env",
        default="MIGRATION_TARGET_URL",
        help="Nome da variável de ambiente com a URL PostgreSQL.",
    )
    mode = migrate.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "check-migrations":
        from sqlalchemy import text

        from app.services.health import expected_revision

        expected = expected_revision()
        with SessionLocal() as db:
            actual = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if actual != expected:
            raise SystemExit("Migrations pendentes. Execute alembic upgrade head após backup.")
        print("Migrations OK.")
    elif args.command == "migrate-sqlite-to-postgres":
        from app.services.migration import migrate_sqlite

        target = os.environ.get(args.target_env)
        if not target:
            raise SystemExit(
                "Defina a variável de destino PostgreSQL. A conexão não será impressa."
            )
        try:
            report = migrate_sqlite(args.source, target, apply=args.apply)
        except Exception as exc:
            from app.services.migration import MigrationConflict

            raise SystemExit(
                str(exc)
                if isinstance(exc, MigrationConflict)
                else "Migração falhou; nenhuma escrita parcial foi confirmada. Confira caminhos, conexão e migrations."
            ) from None
        print("APLICADO" if args.apply else "DRY-RUN: transação revertida; destino preservado.")
        print(json.dumps(report, indent=2))
    elif args.command == "ai-smoke":
        from typing import Literal

        from openai import OpenAI

        from app.schemas import Schema

        class Smoke(Schema):
            status: Literal["ok"]

        cfg = settings()
        if not cfg.openai_api_key:
            raise SystemExit(
                "IA não configurada: defina OPENAI_API_KEY e AI_MODEL no .env da raiz."
            )
        try:
            with OpenAI(api_key=cfg.openai_api_key, timeout=30, max_retries=0) as client:
                response = client.responses.parse(
                    model=cfg.ai_model,
                    store=False,
                    input="Retorne status ok para verificar conectividade e schema. Nenhum dado pessoal está presente.",
                    text_format=Smoke,
                    max_output_tokens=512,
                )
            if response.output_parsed is None or response.output_parsed.status != "ok":
                raise ValueError("Invalid output")
        except Exception:
            raise SystemExit(
                "Falha no smoke de IA. Verifique chave, acesso ao modelo, saldo e suporte a Structured Outputs. Nenhum segredo foi registrado."
            ) from None
        print(
            "IA real OK: Structured Output validado. Tokens:",
            response.usage.total_tokens if response.usage else "não informados",
        )
    elif args.command == "reset-password":
        password = getpass.getpass("Nova senha (mínimo 12 caracteres): ")
        if (
            len(password) < 12
            or len(password) > 128
            or password != getpass.getpass("Confirme a senha: ")
        ):
            raise SystemExit("Senha inválida ou confirmação diferente.")
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == args.email.lower()))
            if not user:
                raise SystemExit("Conta não encontrada.")
            user.password_hash = hasher.hash(password)
            db.execute(delete(SessionToken).where(SessionToken.user_id == user.id))
            db.commit()
        print("Senha atualizada. Todas as sessões desta conta foram encerradas.")
    elif args.command == "backup-sqlite":
        from sqlalchemy.engine import make_url

        url = make_url(settings().database_url)
        if url.get_backend_name() != "sqlite":
            raise SystemExit("Para PostgreSQL use pg_dump conforme docs/DEPLOYMENT.md.")
        destination = Path(args.destination).resolve()
        if destination.exists():
            raise SystemExit("O destino já existe. Escolha um novo nome para preservar backups.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not url.database or not Path(url.database).is_file():
            raise SystemExit("Banco SQLite não encontrado. Nenhum arquivo vazio será criado.")
        with destination.open("xb"):
            pass
        try:
            with (
                closing(
                    sqlite3.connect(Path(url.database).resolve().as_uri() + "?mode=ro", uri=True)
                ) as source,
                closing(sqlite3.connect(destination)) as target,
            ):
                source.backup(target)
                if (
                    target.execute("PRAGMA quick_check").fetchone()[0] != "ok"
                    or target.execute("PRAGMA foreign_key_check").fetchall()
                ):
                    raise RuntimeError("Backup não passou na verificação de integridade.")
        except Exception:
            destination.unlink(missing_ok=True)
            raise SystemExit(
                "Backup falhou; cópia incompleta removida, original preservado."
            ) from None
        print("Backup criado em", destination)


if __name__ == "__main__":
    main()
