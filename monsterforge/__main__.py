"""Run the character constructor from a standalone source checkout."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Monster Forge character constructor')
    assets = parser.add_mutually_exclusive_group()
    assets.add_argument('--demo', action='store_true', help='Generate a small library in /tmp; no game checkout needed')
    assets.add_argument('--asset-root', type=Path, help='Release directory containing media/catalog.json')
    parser.add_argument('--mode', choices=('auto', 'library', 'authoring'))
    parser.add_argument('--host', default=os.environ.get('FLASK_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('FLASK_PORT', '5050')))
    args = parser.parse_args(argv)
    config = {}
    if args.demo:
        from .demo import create_demo
        config.update(ASSET_ROOT=create_demo(), MODE='library')
        if args.mode not in {None, 'library'}:
            parser.error('--demo is a library example; use an asset release for authoring')
    elif args.asset_root is not None:
        config['ASSET_ROOT'] = args.asset_root
    if args.mode is not None:
        config['MODE'] = args.mode
    from . import create_app
    app = create_app(config)
    app.run(host=args.host, port=args.port,
            debug=os.environ.get('FLASK_DEBUG', '0') == '1', use_reloader=False)


if __name__ == '__main__':
    main()
