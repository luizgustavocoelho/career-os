"""Production preflight. Captures Compose config privately; never prints secrets."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "-f", "compose.yaml", "-f", "compose.production.yaml"]


def check(config):
    failures = []
    services = config.get("services", {})
    db = services.get("db", {}).get("environment", {})
    caddy = services.get("caddy", {}).get("environment", {})
    domain = caddy.get("DOMAIN", "")
    if not re.fullmatch(
        r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}", domain
    ):
        failures.append("DOMAIN deve conter um domínio público válido, sem protocolo.")
    password = db.get("POSTGRES_PASSWORD", "")
    if len(password) < 24 or not password.isalnum():
        failures.append(
            "POSTGRES_PASSWORD deve ter pelo menos 24 caracteres alfanuméricos exclusivos."
        )
    if not caddy.get("ACME_EMAIL") or "@" not in caddy["ACME_EMAIL"]:
        failures.append("Configure ACME_EMAIL.")
    for name in ("api", "worker"):
        env = services.get(name, {}).get("environment", {})
        if (
            env.get("ENVIRONMENT") != "production"
            or str(env.get("COOKIE_SECURE")).lower() != "true"
        ):
            failures.append(name + ": produção exige cookies Secure.")
        if (
            env.get("APP_ORIGIN") != "https://" + domain
            or env.get("ALLOWED_ORIGINS") != "https://" + domain
        ):
            failures.append(name + ": origens devem corresponder ao domínio HTTPS.")
        if not env.get("DATABASE_URL", "").startswith("postgresql"):
            failures.append(name + ": banco deve ser PostgreSQL.")
        if str(env.get("REGISTRATION_ENABLED", "")).lower() != "false":
            failures.append(
                name + ": feche cadastros após criar sua conta local e migrá-la."
            )
    if services.get("db", {}).get("ports") or services.get("api", {}).get("ports"):
        failures.append("API e banco devem permanecer sem portas públicas.")
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Também consulta migrations no container e health HTTPS.",
    )
    args = parser.parse_args()
    if not shutil.which("docker"):
        raise SystemExit(
            "Docker/Compose não instalado. Instale-os antes do preflight de produção."
        )
    result = subprocess.run(
        COMPOSE + ["config", "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode:
        raise SystemExit(
            "Compose inválido. Confira .env, DOMAIN, ACME_EMAIL e POSTGRES_PASSWORD; saída omitida para preservar segredos."
        )
    config = json.loads(result.stdout)
    failures = check(config)
    if args.live and not failures:
        result = subprocess.run(
            COMPOSE
            + ["exec", "-T", "api", "python", "-m", "app.manage", "check-migrations"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode:
            failures.append("Migrations/container da API não estão saudáveis.")
        domain = config["services"]["caddy"]["environment"]["DOMAIN"]
        try:
            with urllib.request.urlopen(
                "https://" + domain + "/api/health", timeout=15
            ) as response:
                if json.load(response).get("status") != "ok":
                    failures.append("Health HTTPS indisponível.")
        except (OSError, ValueError):
            failures.append("Health HTTPS não acessível ou certificado inválido.")
    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1
    print(
        "OK: configuração de produção validada."
        + (
            " Migrations e health HTTPS verificados."
            if args.live
            else " Use --live após subir a stack para verificar migrations e health."
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
