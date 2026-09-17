"""Local administrative commands; requires filesystem/database administrator access."""

import argparse
import getpass
import sqlite3
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
    args = parser.parse_args()
    if args.command == "reset-password":
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
        with sqlite3.connect(url.database) as source, sqlite3.connect(destination) as target:
            source.backup(target)
        print("Backup criado em", destination)


if __name__ == "__main__":
    main()
