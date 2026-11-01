"""Canonical JSON shared by assembly identities, storage and publication.

Changing these bytes changes existing content-addressed revision identifiers.
"""

import json


def encoded(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
