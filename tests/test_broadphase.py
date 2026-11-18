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


# ===== 边界与退化场景 =====


def test_zero_size_box():
    # 零尺寸盒 lo == hi：与覆盖该点的盒子相交，与不相交的盒子无对
    boxes = [
        AABB(0, (1.0, 1.0), (1.0, 1.0)),   # 零尺寸，落在盒 1 内
        AABB(1, (0.0, 0.0), (2.0, 2.0)),
        AABB(2, (5.0, 5.0), (5.0, 5.0)),   # 零尺寸，孤立
    ]
    sp = broadphase.sweep_prune(boxes)
    assert set(sp.pairs()) == {(0, 1)}
    assert set(sp.pairs()) == set(broadphase.verify_brute(boxes))


def test_zero_size_touching_edge():
    # 零尺寸盒贴边接触（闭区间）也算重叠，结果确定
    boxes = [
        AABB(0, (2.0, 0.5), (2.0, 0.5)),
        AABB(1, (0.0, 0.0), (2.0, 1.0)),
    ]
    assert set(broadphase.sweep_prune(boxes).pairs()) == {(0, 1)}


def test_coincident_boxes():
    # 完全重合的盒子必成对，且与暴力一致
    boxes = [
        AABB(0, (0.0, 0.0), (1.0, 1.0)),
        AABB(1, (0.0, 0.0), (1.0, 1.0)),
        AABB(2, (0.0, 0.0), (1.0, 1.0)),
    ]
    sp = broadphase.sweep_prune(boxes)
    assert set(sp.pairs()) == {(0, 1), (0, 2), (1, 2)}
    assert sp.pairs() == broadphase.verify_brute(boxes)


def test_empty_scene():
    assert broadphase.sweep_prune([]).pairs() == []
    assert broadphase.build_scene([])["pairs"] == []
    assert broadphase.pair_stats([]) == {"suspected": 0, "confirmed": 0, "missed": 0}


# ===== 输出确定性 =====


def test_deterministic_repeat():
    boxes = _boxes(10, gap=0.6)
    first = broadphase.sweep_prune(boxes).pairs()
    second = broadphase.sweep_prune(boxes).pairs()
    assert first == second  # 不仅集合相同，顺序也相同
    assert first == sorted(first)


def test_stable_sort_tie_by_id():
    # 同起点盒子按编号定序，两次构造结果一致
    boxes = [AABB(i, (0.0, 0.0), (float(i + 1), 1.0)) for i in (3, 1, 2, 0)]
    a = broadphase.sweep_prune(boxes).pairs()
    b = broadphase.sweep_prune(list(reversed(boxes))).pairs()
    assert a == b


# ===== 增量：扫描计数与不全排 =====


def test_update_reports_scans_no_full_resort():
    boxes = _boxes(8)
    sc = broadphase.build_scene(boxes)
    upd = broadphase.update_scene(sc, moved=[AABB(3, (0.2, 0.0), (1.7, 1.0, 1.0))])
    assert upd["scans"] > 0            # 报告了扫描次数
    assert upd["sorts"] == 1           # 没有发生新的全量排序
    assert upd["scans"] < sc["scans"] + len(boxes) * 4  # 远低于全量重建量级


def test_update_remove_and_move_together():
    boxes = _boxes(7, gap=0.8)
    sc = broadphase.build_scene(boxes)
    moved = [AABB(0, (5.0, 0.0), (6.5, 1.0, 1.0))]
    upd = broadphase.update_scene(sc, removed_ids={2, 5}, moved=moved)
    rebuilt = [b for b in boxes if b.id not in {0, 2, 5}] + moved
    assert sorted(upd["pairs"]) == sorted(broadphase.build_scene(rebuilt)["pairs"])
    for p in upd["pairs"]:
        assert 2 not in p and 5 not in p


def test_update_incremental_equals_rebuild_repeatedly():
    boxes = _boxes(6, gap=0.9)
    sc = broadphase.build_scene(boxes)
    cur = list(boxes)
    for step in range(3):
        moved = [AABB(step, (2.5 + step, 0.0), (3.5 + step, 1.0, 1.0))]
        sc = broadphase.update_scene(sc, moved=moved)
        cur = [b for b in cur if b.id != step] + moved
        assert sorted(sc["pairs"]) == sorted(broadphase.build_scene(cur)["pairs"])


# ===== 睡眠 / 唤醒 =====


def test_sleep_multiple_and_partial_wake():
    boxes = _boxes(5, gap=0.7)
    full = sorted(broadphase.build_scene(boxes)["pairs"])
    sc = broadphase.sleep_scene(broadphase.build_scene(boxes), {1, 3})
    assert all(1 not in p and 3 not in p for p in sc["pairs"])
    # 只唤醒 1：候选 = 全量中不含 3 的部分
    part = broadphase.wake_scene(sc, {1})
    assert sorted(part["pairs"]) == [p for p in full if 3 not in p]
    # 再唤醒 3：与全量一致
    done = broadphase.wake_scene(part, {3})
    assert sorted(done["pairs"]) == full


def test_sleep_then_move_sleeping_box():
    boxes = _boxes(4)
    sc = broadphase.sleep_scene(broadphase.build_scene(boxes), {2})
    upd = broadphase.update_scene(sc, moved=[AABB(2, (0.1, 0.0), (1.6, 1.0, 1.0))])
    assert all(2 not in p for p in upd["pairs"])  # 睡眠盒子仍不产生候选
    woken = broadphase.wake_scene(upd, {2})
    rebuilt = [b for b in boxes if b.id != 2] + [AABB(2, (0.1, 0.0), (1.6, 1.0, 1.0))]
    assert sorted(woken["pairs"]) == sorted(broadphase.build_scene(rebuilt)["pairs"])


# ===== 预算化 =====


def test_budgeted_budget_one():
    boxes = _boxes(6, gap=0.6)
    full = sorted(broadphase.build_scene(boxes)["pairs"])
    acc, r = [], broadphase.budgeted_pairs(boxes, 1)
    guard = 0
    while True:
        acc.extend(r["pairs"])
        guard += 1
        if r["done"] or guard > 100:
            break
        r = broadphase.budgeted_pairs(boxes, 1, cursor=r["cursor"])
    assert r["done"]
    assert sorted(set(acc)) == full


def test_budgeted_large_budget_single_pass():
    boxes = _boxes(5)
    r = broadphase.budgeted_pairs(boxes, 10 ** 6)
    assert r["done"] and r["cursor"] is None
    assert sorted(r["pairs"]) == sorted(broadphase.build_scene(boxes)["pairs"])


def test_budgeted_reports_scans_and_incomplete():
    boxes = _boxes(8)
    r = broadphase.budgeted_pairs(boxes, 2)
    assert not r["done"]
    assert r["scans"] == 2  # 预算即扫描次数
    assert r["cursor"] is not None


def test_budgeted_empty_and_single():
    assert broadphase.budgeted_pairs([], 1)["done"]
    r = broadphase.budgeted_pairs([AABB(0, (0, 0), (1, 1))], 1)
    assert r["done"] and r["pairs"] == []


# ===== 统计 =====


def test_stats_on_data_file():
    boxes = broadphase.load_boxes("data/boxes.json")
    st = broadphase.pair_stats(boxes)
    assert st["missed"] == 0
    assert st["suspected"] >= st["confirmed"]
    assert st["confirmed"] == len(broadphase.verify_brute(boxes))


def test_stats_suspected_counts_axis_only():
    # 盒 0、1 在 x 轴重叠但 y 轴分离：疑似 +1，确认不变
    boxes = [
        AABB(0, (0.0, 0.0), (1.0, 1.0)),
        AABB(1, (0.5, 5.0), (1.5, 6.0)),
    ]
    st = broadphase.pair_stats(boxes)
    assert st["suspected"] == 1
    assert st["confirmed"] == 0
    assert st["missed"] == 0
