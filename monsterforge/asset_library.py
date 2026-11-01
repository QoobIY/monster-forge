"""Shared project pages and versioned, read-only media access."""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
)

from monster_forge_sdk import AssetIntegrityError, AssetNotFound, AssetStore

blueprint = Blueprint("asset_library", __name__)


def catalog_stamp(assets: AssetStore) -> tuple[int, int, int, int] | None:
    try:
        info = (assets.media_root / "catalog.json").stat()
    except FileNotFoundError:
        return None
    return info.st_mtime_ns, info.st_ctime_ns, info.st_size, info.st_ino


def store() -> AssetStore:
    # Read the catalog only after publication. Geometry and file requests must
    # use the same release as the library listing, without restarting Flask.
    with current_app.extensions["asset_store_lock"]:
        assets = current_app.extensions["asset_store"]
        stamp = catalog_stamp(assets)
        if stamp != current_app.extensions["asset_store_stamp"]:
            replacement = AssetStore(
                assets.root,
                cache_dir=assets.cache.root if assets.cache else None,
                catalog=b'{"schema_version":1,"assets":[]}' if stamp is None else None,
            )
            if catalog_stamp(replacement) != stamp:
                raise AssetIntegrityError("Asset catalog changed while loading; retry")
            current_app.extensions["asset_store"] = replacement
            current_app.extensions["asset_store_stamp"] = stamp
            assets = replacement
        return assets


@blueprint.get("/characters/")
def characters():
    if not current_app.extensions["capabilities"]["constructor"]["available"]:
        return render_template("constructor_setup.html", active="characters")
    return render_template("characters.html", active="characters")


@blueprint.get("/icons/")
def icons():
    return render_template(
        "library.html",
        active="icons",
        kind="icon",
        heading="Иконки",
        description="Предметы, способности, эффекты и интерфейс. Выбирай глазами.",
    )


@blueprint.get("/decorations/")
def decorations():
    return render_template(
        "library.html",
        active="decorations",
        kind="decoration",
        heading="Декорации",
        description="Окружение для игровых сцен. Настоящие модели, масштаб и материалы.",
    )


@blueprint.get("/terrain/")
def terrain():
    return render_template("library.html", active="terrain", kind="terrain",
                           heading="Ландшафт", description="Бесшовные тайлы земли и клифов. Общие материалы для карт.")


@blueprint.get("/sdk/")
def sdk():
    return render_template("sdk.html", active="sdk")


@blueprint.get("/api/assets/v1/catalog")
def catalog():
    kind = request.args.get("kind")
    if kind is not None and kind not in {"character", "icon", "decoration", "terrain", "audio"}:
        return jsonify(error="Unknown asset kind"), 400
    response = jsonify(store().catalog(kind))
    response.headers["Cache-Control"] = "no-store"
    return response


@blueprint.get("/api/assets/v1/icon-style")
def icon_style():
    try:
        return jsonify(store().icon_style())
    except AssetIntegrityError as error:
        return jsonify(error=str(error)), 409


@blueprint.get("/styles/icons/<filename>")
def style_file(filename):
    if filename not in {
        "style.txt",
        "profile.json",
        "prompts-mom.json",
        "prompts.json",
        "mom-style-reference.jpg",
    }:
        abort(404)
    try:
        profile = store().icon_style()
    except AssetIntegrityError as error:
        return jsonify(error=str(error)), 409
    actual = {"style.txt": profile["source"], "mom-style-reference.jpg": profile["reference"]}.get(filename, filename)
    return send_file(store().root / "styles/icons" / actual, conditional=True)


@blueprint.get("/media/<path:filename>")
def media_file(filename):
    try:
        path = store().resolve_uri("/media/" + filename)
    except AssetNotFound:
        abort(404)
    except AssetIntegrityError as error:
        return jsonify(error=str(error)), 409
    response = send_file(
        path, conditional=True, as_attachment=request.args.get("download") == "1"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-cache"
    return response


@blueprint.get("/api/assets/v1/geometry")
def scene_geometry():
    from .asset_geometry import geometry

    identifier = request.args.get("id", "")
    try:
        assets = store()
        return jsonify(geometry(identifier, assets.release_id, root=assets.root))
    except AssetNotFound:
        abort(404)
    except (ValueError, AssetIntegrityError) as error:
        return jsonify(error=str(error)), 409
