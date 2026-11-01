from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh

from monsterforge.skin_weights import build_weight_sidecar, write_weight_sidecar


class SkinWeightTest(unittest.TestCase):
    def test_limb_weights_are_normalized_and_stay_inside_slot_palette(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "arm.glb"
            mesh = trimesh.creation.box(extents=[0.2, 1.2, 0.2])
            path.write_bytes(trimesh.Scene(mesh).export(file_type="glb"))
            payload = build_weight_sidecar(path, "left_arm")
            self.assertEqual(len(mesh.vertices), payload["vertex_count"])
            self.assertEqual(
                {"left_shoulder", "left_elbow", "left_hand"},
                set(payload["allowed_bones"]) & {"left_shoulder", "left_elbow", "left_hand"},
            )
            weights = np.asarray(payload["skin_weights"])
            indices = np.asarray(payload["skin_indices"])
            self.assertTrue(np.allclose(weights.sum(axis=1), 1.0))
            palette = payload["bone_palette"]
            used = {palette[int(index)] for index in indices[weights > 0]}
            self.assertLessEqual(used, set(payload["allowed_bones"]))

    def test_sidecar_is_tied_to_immutable_model_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "leg.glb"
            model.write_bytes(trimesh.Scene(trimesh.creation.box(extents=[0.2, 1.4, 0.25])).export(file_type="glb"))
            payload = write_weight_sidecar(model, "right_leg")
            self.assertEqual(payload["model_sha256"], build_weight_sidecar(model, "right_leg")["model_sha256"])
            self.assertTrue((root / "weights.json").is_file())
