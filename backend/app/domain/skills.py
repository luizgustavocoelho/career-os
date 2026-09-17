import re
import unicodedata

ALIASES = {
    "python3": "python",
    "python 3": "python",
    "py": "python",
    "postgres": "postgresql",
    "postgre sql": "postgresql",
    "js": "javascript",
    "ts": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "amazon web services": "aws",
    "microsoft azure": "azure",
    "google cloud platform": "gcp",
    "apache airflow": "airflow",
    "apache spark": "spark",
    "powerbi": "power bi",
    "ci cd": "ci/cd",
    "k8s": "kubernetes",
    "scikit learn": "scikit-learn",
}


def normalize(value: str) -> str:
    plain = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    plain = re.sub(r"\s+", " ", plain.lower().strip())
    return ALIASES.get(plain, plain)


def canonical_url(url: str | None) -> str:
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if not k.startswith("utm_") and k not in {"ref", "source"}
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(sorted(query)),
            "",
        )
    )


def fingerprint(data: dict) -> str:
    import hashlib

    # Company/title/location remain useful when the same vacancy has multiple URLs.
    parts = [normalize(data.get(k) or "") for k in ("company", "title", "location")]
    parts.append(normalize(data.get("description", "")))
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
