# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import broadphase as mod  # noqa: E402


def test_pairs_match_brute():
    boxes = broadphase.load_boxes("data/boxes.json")
    sp = broadphase.sweep_prune(boxes)
    got = set(sp.pairs())
    want = set(broadphase.verify_brute(boxes))
    assert got == want


def test_single_box():
    sp = broadphase.sweep_prune([broadphase.AABB(0, (0, 0), (1, 1))])
    assert sp.pairs() == []


# ===== v2 契约测试：初始全部失败，实现后必须通过 =====
import broadphase  # noqa: E402
AABB = broadphase.AABB



def _boxes(n, gap=1.0, span=1.5):
    return [AABB(i, (i * gap, 0.0, 0.0), (i * gap + span, 1.0, 1.0)) for i in range(n)]


def test_scene_pairs_reported():
    sc = broadphase.build_scene(_boxes(4))
    assert "pairs" in sc and "boxes" in sc
    assert all(isinstance(p, tuple) and len(p) == 2 for p in sc["pairs"])


def test_update_after_removal_matches_rebuild():
    boxes = _boxes(6)
    sc = broadphase.build_scene(boxes)
    removed = {1, 4}
    upd = broadphase.update_scene(sc, removed_ids=removed)
    kept = [b for b in boxes if b.id not in removed]
    assert sorted(upd["pairs"]) == sorted(broadphase.build_scene(kept)["pairs"])
    for p in upd["pairs"]:
        assert not (set(p) & removed)


def test_update_after_move_matches_rebuild():
    boxes = _boxes(5)
    sc = broadphase.build_scene(boxes)
    moved = [AABB(2, (0.4, 0.0, 0.0), (1.9, 1.0, 1.0))]
    upd = broadphase.update_scene(sc, moved=moved)
    rebuilt = [b for b in boxes if b.id != 2] + moved
    assert sorted(upd["pairs"]) == sorted(broadphase.build_scene(rebuilt)["pairs"])


def test_sleep_excludes_and_wake_restores():
    boxes = _boxes(4)
    full = sorted(broadphase.build_scene(boxes)["pairs"])
    slept = broadphase.sleep_scene(broadphase.build_scene(boxes), {2})
    assert all(2 not in p for p in slept["pairs"])
    woken = sorted(broadphase.wake_scene(slept, {2})["pairs"])
    assert woken == full


def test_budgeted_accumulates_to_full():
    boxes = _boxes(8, gap=0.7)
    full = sorted(broadphase.build_scene(boxes)["pairs"])
    acc = []
    r = broadphase.budgeted_pairs(boxes, 3)
    guard = 0
    while True:
        acc.extend(r["pairs"])
        guard += 1
        if r["done"] or guard > 60:
            break
        r = broadphase.budgeted_pairs(boxes, 3, cursor=r.get("cursor"))
    assert sorted(set(acc)) == full


def test_stats_no_miss():
    boxes = _boxes(6, gap=0.5)
    st = broadphase.pair_stats(boxes)
    assert st["missed"] == 0
    assert st["confirmed"] == len(broadphase.build_scene(boxes)["pairs"])
    assert st["suspected"] >= st["confirmed"]
