"""Original constructor choices and exports work from a cold source pack, without MoM."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monsterforge.resources import MANIFEST, load_resources, verify_resources


class ResourceInventoryTests(unittest.TestCase):
    def test_metadata_only_reader_and_separate_payload_integrity_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "config/constructor_library_v1.json"
            source.parent.mkdir()
            source.write_bytes(b"{}")
            spec = {"sha256": hashlib.sha256(b"{}").hexdigest(), "size_bytes": 2,
                    "classification": "configuration"}
            (root / MANIFEST).write_text(json.dumps({"schema_version": 1, "resources": {
                source.relative_to(root).as_posix(): spec,
            }}))
            original = Path.read_bytes

            def guarded_read(path):
                if path == source:
                    raise AssertionError("Metadata reader opened a resource payload")
                return original(path)

            with patch.object(Path, "read_bytes", guarded_read):
                self.assertEqual(load_resources(root)[source.relative_to(root).as_posix()], spec)
            self.assertEqual(verify_resources(root), [])
            source.write_bytes(b"[]")
            self.assertTrue(any("hash changed" in error for error in verify_resources(root)))
            source.unlink()
            source.symlink_to(root / MANIFEST)
            self.assertTrue(any("symlinks" in error for error in verify_resources(root)))

    def test_unknown_schema_and_non_source_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            spec = {"sha256": "a" * 64, "size_bytes": 1, "classification": "recipe"}
            for version, name in ((99, "media/constructor/example/recipe.json"),
                                  (True, "media/constructor/example/recipe.json"),
                                  (1, "media/constructor/../../.env"),
                                  (1, "media/constructor/example/head.weights.json"),
                                  (1, "media/constructor/example/tool-response.json")):
                (root / MANIFEST).write_text(json.dumps({"schema_version": version, "resources": {name: spec}}))
                with self.subTest(version=version, name=name), self.assertRaises(ValueError):
                    load_resources(root)


class ExistingStandaloneConstructorTests(unittest.TestCase):
    def test_cold_original_catalog_human_and_centaur_exports_without_game_package(self):
        root = Path(__file__).resolve().parents[1]
        resources = load_resources(root)
        self.assertGreaterEqual(len(resources), 3000)
        self.assertEqual(sum(name.endswith("/front.png") and "/attribute_references/" in name
                             for name in resources), 27)
        with tempfile.TemporaryDirectory(prefix="forge-standalone-source-", dir="/tmp") as temporary:
            work = Path(temporary)
            source = work / "source"
            source.mkdir()
            for directory in ("monsterforge", "monster_forge_sdk", "tools/assets", "tools/creature_workshop"):
                shutil.copytree(root / directory, source / directory,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            inputs = [*resources, MANIFEST, "config/style_profile.json", "config/humanoid_v1.json",
                      "media/rigs/body_rigs.json", "media/rigs/humanoid/canonical.json",
                      "media/rigs/humanoid/workshop_knees_v1.json"]
            for name in inputs:
                destination = source / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / name, destination)
            self.assertFalse(any((source / "media").rglob("*.glb")))
            self.assertFalse(any((source / "media").rglob("*.weights.json")))
            script = r'''
import base64, copy, hashlib, importlib.abc, io, json, os, shutil, sys, zipfile
from pathlib import Path
class NoGame(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'machine_of_monsters' or fullname.startswith('machine_of_monsters.'):
            raise AssertionError('Constructor attempted to import the game: ' + fullname)
sys.meta_path.insert(0, NoGame())
source = Path(sys.argv[1])
work = Path(sys.argv[2])
sys.path.insert(0, str(source))
import numpy as np
import trimesh
from monsterforge.assembly_repository import AssemblyRepository
from monsterforge.constructor.service import ConstructorService
from monsterforge.paths import cache_directory
from monsterforge.resources import load_resources, verify_resources
from monster_forge_sdk.characters import load_skeleton, read_character_model
from tools.assets.bake_character_models import accessor, bone_matrices, unpack
import monsterforge
assert Path(monsterforge.__file__).is_relative_to(source)
inputs = load_resources(source)
before = {name: (source / name).stat().st_mtime_ns for name in inputs}
cache = cache_directory(root=source)
assert not cache.exists(), 'Numerical check must start with a cold cache'
try:
    service = ConstructorService(repository=AssemblyRepository(work / 'saved'))
    catalog = service.catalog()
    expected_races = {'human','skeleton','minotaur','orc','goblin','ghost','golem','panda','beorn','kobold','quillboar','spider','beast-sheep','beast-wolf','beast-bear','beast-boar','beast-dog','beast-tiger','beast-horse','sky-dragon','sky-bone-dragon','sky-eagle','naga','centaur','beast-elephant','crab','beetle','scorpion','tree','randomium','frog','slime','satyr'}
    assert expected_races <= {race['id'] for race in catalog['races']}
    assert len(catalog['presets']) >= 193
    human = copy.deepcopy(catalog['active_defaults'])
    assert human['schema_version'] == 5 and human['race'] == 'human'
    human_snapshot = copy.deepcopy(human)
    preview = service.preview(human)
    assert preview['triangles'] > 0 and human == human_snapshot
    instruction, blob = service.compact_assembly(human, work / 'human')
    assert instruction['schema_version'] == 2
    assert instruction['constructor_settings'] == human_snapshot
    assert instruction['model']['sha256'] == hashlib.sha256(blob).hexdigest()
    model = read_character_model(blob)
    attrs = model['attributes']
    palette = model['metadata']['bone_palette']
    np.testing.assert_allclose(np.sum(attrs['WEIGHTS_0'], axis=1), 1, atol=1.e-6)
    allowed = load_skeleton()['slot_bindings']
    offset = 0
    for slot in ('head','torso','left_arm','right_arm','left_leg','right_leg'):
        folder = work / 'human/parts' / slot
        doc, binary = unpack((folder / 'model.glb').read_bytes())
        positions = accessor(doc, binary, doc['meshes'][0]['primitives'][0]['attributes']['POSITION'])
        skin = json.loads((folder / 'weights.json').read_bytes())
        count = len(positions)
        np.testing.assert_array_equal(attrs['POSITION'][offset:offset+count], positions)
        np.testing.assert_allclose(attrs['WEIGHTS_0'][offset:offset+count], skin['skin_weights'], atol=1.e-7)
        names = [palette.index(name) for name in skin['bone_palette']]
        joints = np.asarray(names)[skin['skin_indices']]
        np.testing.assert_array_equal(attrs['JOINTS_0'][offset:offset+count], joints)
        positive = np.asarray(skin['skin_weights']) > 0
        assert {palette[index] for index in joints[positive]} <= set(allowed[slot]['allowed_bones'])
        if slot in {'left_leg','right_leg'}:
            assert abs(positions[:,1].min()) < 1.e-5
        offset += count
    assert offset == model['metadata']['vertex_count']
    for world, inverse in zip(bone_matrices(model['metadata']['skeleton']), model['inverse_bind_matrices'], strict=True):
        np.testing.assert_allclose(world @ np.asarray(inverse).reshape(4,4).T, np.eye(4), atol=1.e-5)
    with zipfile.ZipFile(io.BytesIO(service.export_bundle(human))) as archive:
        assert set(archive.namelist()) == {'assembly.json','model.glb'}
        assert archive.read('model.glb') == blob
    centaur = copy.deepcopy(next(p['settings'] for p in catalog['presets'] if p['settings']['race'] == 'centaur'))
    centaur_snapshot = copy.deepcopy(centaur)
    centaur_preview = service.preview(centaur)
    assert centaur_preview['triangles'] > 0
    assert centaur_preview['checks']['weight_sidecars'] is False
    static_instruction, static_blob = service.compact_assembly(centaur, work / 'centaur')
    assert static_instruction['schema_version'] == 2
    assert static_instruction['constructor_settings'] == centaur_snapshot
    assert static_instruction['rigging'] == 'none' and static_instruction['runtime_support'] is False
    assert static_instruction['status'] == 'authoring_draft'
    document, _ = unpack(static_blob)
    assert not document.get('skins') and not document.get('animations')
    for mesh in document['meshes']:
        for primitive in mesh['primitives']:
            assert 'JOINTS_0' not in primitive['attributes'] and 'WEIGHTS_0' not in primitive['attributes']
    def triangles(data):
        scene = trimesh.load(io.BytesIO(data), file_type='glb', force='scene', process=False)
        return np.concatenate([trimesh.transform_points(scene.geometry[scene.graph[node][1]].vertices, scene.graph[node][0])[scene.geometry[scene.graph[node][1]].faces].reshape(-1,3)
                               for node in scene.graph.nodes_geometry]).astype('<f4')
    originals = np.concatenate([triangles(path.read_bytes()) for path in sorted((work / 'centaur/parts').glob('*/model.glb'))])
    merged = triangles(static_blob)
    assert len(merged) == len(originals) == centaur_preview['triangles'] * 3
    def ordered(values):
        return values[np.lexsort((values[:,2],values[:,1],values[:,0]))]
    np.testing.assert_array_equal(ordered(merged), ordered(originals))
    with zipfile.ZipFile(io.BytesIO(service.export_bundle(centaur))) as archive:
        assert set(archive.namelist()) == {'assembly.json','model.glb'}
        assert archive.read('model.glb') == static_blob
    saved = service.save(centaur)
    assert service.saved_manifest(saved['id'])['constructor_settings'] == centaur_snapshot
    assert service.saved_model(saved['id']) == static_blob
    assert service.save(centaur) == saved
    assert centaur == centaur_snapshot and human == human_snapshot
    for changed in ({**human, 'placement':[0,0,0]}, {**human, 'schema_version':999}):
        try:
            service.preview(changed)
        except ValueError:
            pass
        else:
            raise AssertionError('Incompatible settings were silently accepted')
    assert verify_resources(source) == []
    assert all((source / name).stat().st_mtime_ns == stamp for name,stamp in before.items())
    assert not any((source / 'media').rglob('*.glb'))
    assert not any(name == 'machine_of_monsters' or name.startswith('machine_of_monsters.') for name in sys.modules)
    assert cache.is_relative_to('/tmp') and not cache.is_relative_to(source)
    print(json.dumps({'races':len(catalog['races']),'presets':len(catalog['presets']),'human_vertices':model['metadata']['vertex_count'],'centaur_triangles':len(merged)//3,'source_resources':len(inputs),'game_imported':False}))
finally:
    shutil.rmtree(cache, ignore_errors=True)
'''
            environment = os.environ.copy()
            environment.pop("MONSTER_FORGE_ASSET_ROOT", None)
            result = subprocess.run([sys.executable, "-I", "-B", "-c", script, str(source), str(work)],
                                    cwd=work, env=environment, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertFalse(report["game_imported"])
            self.assertEqual(report["source_resources"], len(resources))
