from datetime import datetime

from sqlalchemy import inspect


def serialize(obj, exclude=()):
    result = {}
    for col in inspect(obj).mapper.column_attrs:
        key = col.key
        if key in {"password_hash", "content", "token_hash", "csrf_token", "user_id"} | set(
            exclude
        ):
            continue
        value = getattr(obj, key)
        if isinstance(value, datetime):
            value = value.isoformat() + "Z"
        result[key] = value
    return result
