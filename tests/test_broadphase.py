# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import broadphase as mod  # noqa: E402

def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_hex(path):
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def test_pairs_match_brute():
    boxes = broadphase.load_boxes("data/boxes.json")
    sp = broadphase.sweep_prune(boxes)
    got = set(sp.pairs())
    want = set(broadphase.verify_brute(boxes))
    assert got == want


def test_single_box():
    sp = broadphase.sweep_prune([broadphase.AABB(0, (0, 0), (1, 1))])
    assert sp.pairs() == []
