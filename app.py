#!/usr/bin/env python3
"""Monster Forge Flask entrypoint."""

from __future__ import annotations

from monsterforge import create_app

if __name__ == "__main__":
    from monsterforge.__main__ import main

    main()
else:
    app = create_app()
