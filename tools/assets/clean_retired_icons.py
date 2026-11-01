"""Audit or delete explicitly retired icons, preserving every shared live file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.assets.icon_policy import canonical_entry, retired_icon

ROOT = Path(__file__).resolve().parents[2]


def clean(root: Path = ROOT, *, apply=False, report: Path | None = None):
    media = root/'media'
    documents = {name: json.loads((media/name).read_text())
                 for name in ('catalog.json', 'imported_catalog.json')}
    retired, live = {}, set()
    for document in documents.values():
        for entry in document['assets']:
            if retired_icon(entry):
                retired[entry['id']] = entry
            else:
                live.update(ref['path'] for ref in entry['files'].values())
    candidates = {ref['path'] for entry in retired.values() for ref in entry['files'].values()}
    owned = set()
    for entry in retired.values():
        parts = Path(entry['files']['image']['path']).parts
        if parts[:2] in (('icons', 'singles'), ('icons', 'collections')):
            owned.add(Path(*parts[:3]))
        if parts[:3] == ('ui', 'icons', 'stats') or parts[:3] == ('ui', 'icons', 'items'):
            owned.add(Path(*parts[:3]))
    for folder in owned:
        candidates.update(p.relative_to(media).as_posix() for p in (media/folder).rglob('*') if p.is_file())
    deleted = sorted(candidates-live)
    for path in deleted:
        file = media/path
        if file.is_symlink() or not file.resolve().is_relative_to(media.resolve()):
            raise ValueError('Retired path escapes the media release: '+path)
    summary = {'removed_ids': sorted(retired), 'deleted_files': deleted,
               'shared_files_preserved': sorted(candidates & live),
               'bytes_removed': sum((media/p).stat().st_size for p in deleted if (media/p).is_file()),
               'nova_icons': sum(canonical_entry(a).get('group') == 'Nova'
                                 for a in documents['catalog.json']['assets'] if not retired_icon(a))}
    if apply:
        for name, document in documents.items():
            document['assets'] = [canonical_entry(a) for a in document['assets'] if a['id'] not in retired]
            if 'aliases' in document:
                document['aliases'] = {k: v for k, v in document['aliases'].items()
                                       if k not in retired and v not in retired}
            (media/name).write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
        for path in deleted:
            (media/path).unlink(missing_ok=True)
        # Only remove directories made empty by this exact deletion plan.
        parents = {parent for path in deleted for parent in (media/path).parents
                   if parent != media and parent.is_relative_to(media)}
        for folder in sorted(parents, key=lambda p: len(p.parts), reverse=True):
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
    if report:
        report.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(f"{'Deleted' if apply else 'Planned'} {len(retired)} icon records, {len(deleted)} files; "
          f"{summary['bytes_removed']} bytes; Nova: {summary['nova_icons']} icons")
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    clean(apply=args.apply, report=args.report)
