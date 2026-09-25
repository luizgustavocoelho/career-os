"""Offline, atomic SQLite-to-PostgreSQL transfer. Never logs row values or URLs."""

import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app import models  # noqa: F401
from app.db import Base


class MigrationConflict(RuntimeError):
    pass


def schema_revision(connection):
    return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def validate_schema(connection):
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        columns = {c["name"] for c in inspector.get_columns(table.name)}
        if columns != set(table.columns.keys()):
            raise MigrationConflict(
                f"Schema incompatível na tabela {table.name}. Aplique migrations em ambos os bancos."
            )


def ordered_rows(table, rows):
    if table.name != "documents":
        return rows
    pending = {row["id"]: row for row in rows}
    ordered = []
    while pending:
        ready = [
            row
            for row in pending.values()
            if not row["parent_id"] or row["parent_id"] not in pending
        ]
        if not ready:
            raise MigrationConflict("Ciclo inválido na linhagem de documentos.")
        for row in ready:
            ordered.append(row)
            del pending[row["id"]]
    return ordered


def transfer(source, target, apply=False):
    """Internal transactional copier; production CLI only accepts PostgreSQL target."""
    report = {}
    with source.connect() as src, target.connect() as dst:
        transaction = dst.begin()
        try:
            if dst.dialect.name == "postgresql":
                dst.execute(text("SELECT pg_advisory_xact_lock(1667330661)"))
                # Block concurrent writes throughout validation and transfer, preserve atomicity.
                names = ", ".join('"' + t.name + '"' for t in Base.metadata.sorted_tables)
                dst.execute(text("LOCK TABLE " + names + " IN SHARE ROW EXCLUSIVE MODE"))
            validate_schema(src)
            validate_schema(dst)
            if schema_revision(src) != schema_revision(dst):
                raise MigrationConflict(
                    "Revisões Alembic diferentes; migre ambos até a mesma revisão."
                )
            if src.dialect.name == "sqlite":
                if (
                    src.exec_driver_sql("PRAGMA quick_check").scalar() != "ok"
                    or src.exec_driver_sql("PRAGMA foreign_key_check").all()
                ):
                    raise MigrationConflict(
                        "Integridade SQLite inválida; preserve o original e restaure um backup verificado."
                    )
            for table in Base.metadata.sorted_tables:
                rows = ordered_rows(
                    table, [dict(row) for row in src.execute(select(table)).mappings()]
                )
                added = equal = 0
                keys = [c.name for c in table.primary_key]
                for row in rows:
                    condition = [table.c[key] == row[key] for key in keys]
                    existing = dst.execute(select(table).where(*condition)).mappings().one_or_none()
                    if existing is not None:
                        if any(existing[key] != value for key, value in row.items()):
                            raise MigrationConflict(
                                f"Conflito de conteúdo em {table.name}; nenhum dado foi sobrescrito."
                            )
                        equal += 1
                    else:
                        # Dry-run uses real constraints then rolls back the complete transaction.
                        dst.execute(table.insert().values(**row))
                        added += 1
                report[table.name] = {"source": len(rows), "new": added, "identical": equal}
                for row in rows:
                    existing = (
                        dst.execute(select(table).where(*(table.c[k] == row[k] for k in keys)))
                        .mappings()
                        .one()
                    )
                    if dict(existing) != row:
                        raise MigrationConflict(f"Verificação pós-cópia falhou em {table.name}.")
            if (
                dst.dialect.name == "sqlite"
                and dst.exec_driver_sql("PRAGMA foreign_key_check").all()
            ):
                raise MigrationConflict("Referências inconsistentes no destino.")
            if apply:
                transaction.commit()
            else:
                transaction.rollback()
        except IntegrityError:
            transaction.rollback()
            raise MigrationConflict(
                "Conflito de chave única ou referência. Nada foi gravado; use destino vazio ou cópia idêntica."
            ) from None
        except Exception:
            transaction.rollback()
            raise
    return report


def migrate_sqlite(source_path, target_url, apply=False):
    from sqlalchemy.engine import make_url

    target_config = make_url(target_url)
    if target_config.get_backend_name() != "postgresql":
        raise MigrationConflict("O destino deve ser PostgreSQL.")
    path = Path(source_path).resolve(strict=True)
    # Backup API includes WAL and gives the transfer an immutable, consistent snapshot.
    with tempfile.TemporaryDirectory(prefix="careeros-migration-") as temporary:
        snapshot = Path(temporary) / "snapshot.db"
        with (
            closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as source,
            closing(sqlite3.connect(snapshot)) as backup,
        ):
            source.backup(backup)
        src = create_engine("sqlite:///" + snapshot.as_posix())
        dst = create_engine(target_config)
        try:
            return transfer(src, dst, apply=apply)
        finally:
            src.dispose()
            dst.dispose()
