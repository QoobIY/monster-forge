"""Standalone character constructor with an optional published asset library."""

import os
from threading import RLock

from flask import Flask, jsonify, redirect, request

from monster_forge_sdk import AssetStore

from .asset_library import blueprint as library_blueprint
from .asset_library import catalog_stamp, store
from .creature_workshop import blueprint as constructor_blueprint
from .paths import ROOT
from .runtime import source_availability


def create_app(config=None):
    """Create an isolated app without requiring another project or asset release."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_mapping(
        ASSET_ROOT=os.environ.get("MONSTER_FORGE_ASSET_ROOT"),
        MODE=os.environ.get("MONSTER_FORGE_MODE", "auto"),
    )
    if config is not None:
        app.config.update(config)
    mode = app.config["MODE"]
    if mode not in {"auto", "library", "authoring"}:
        raise ValueError("MODE must be auto, library or authoring")
    if mode == "library":
        available, reason = False, "Constructor is disabled in library mode"
    elif app.config.get("CONSTRUCTOR_SERVICE") is not None:
        available, reason = True, None
    else:
        available, reason = source_availability()
    if mode == "authoring" and not available:
        raise RuntimeError(reason)
    app.extensions["capabilities"] = {
        "schema_version": 1,
        "mode": "authoring" if available else "library",
        "asset_library": {"available": True},
        "constructor": {"available": available, "reason": reason, "contracts": ["humanoid_v1"]},
    }
    asset_root = app.config["ASSET_ROOT"]
    # The constructor uses its bundled recipes, not a game's published catalog.
    # An explicitly supplied release still has to satisfy the SDK contract.
    empty_library = asset_root is None and not (ROOT / "media/catalog.json").is_file()
    app.extensions["asset_store"] = AssetStore(
        ROOT if empty_library else asset_root,
        catalog=b'{"schema_version":1,"assets":[]}' if empty_library else None,
    )
    app.extensions["asset_store_stamp"] = catalog_stamp(app.extensions["asset_store"])
    app.extensions["asset_store_lock"] = RLock()
    app.register_blueprint(constructor_blueprint)
    app.register_blueprint(library_blueprint)

    @app.context_processor
    def capabilities_context():
        return {"constructor_available": available, "constructor_reason": reason}

    @app.before_request
    def require_constructor():
        if not available and request.path.startswith("/creature-workshop/constructor/"):
            if request.path.rstrip("/") == "/creature-workshop/constructor":
                return redirect("/characters/")
            return jsonify(error=reason, code="constructor_unavailable"), 503

    @app.get("/api/capabilities")
    def capabilities():
        return jsonify(app.extensions["capabilities"])

    @app.get("/")
    def index():
        return redirect("/characters/" if available else "/decorations/")

    @app.get("/health")
    def health():
        return jsonify(
            status="ok",
            service="monster-forge",
            asset_release=store().release_id,
            mode=app.extensions["capabilities"]["mode"],
        )

    return app
