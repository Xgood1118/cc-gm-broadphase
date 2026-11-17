# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import broadphase as mod  # noqa: E402
broadphase = mod
AABB = broadphase.AABB


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
    sp = broadphase.sweep_prune([AABB(0, (0, 0), (1, 1))])
    assert sp.pairs() == []


def test_pairs_match_brute_random_like():
    # 多构造几批（含不重叠、部分重叠、嵌套），候选必须与暴力完全一致
    cases = [
        [AABB(0, (0, 0), (1, 1)), AABB(1, (2, 2), (3, 3))],
        [AABB(0, (0, 0), (2, 2)), AABB(1, (1, 1), (3, 3)),
         AABB(2, (0.5, 0.5), (1.5, 1.5))],
        [AABB(i, (i * 0.5, 0), (i * 0.5 + 1, 1)) for i in range(8)],
        # x 轴相交但 y 轴不相交，不能算对
        [AABB(0, (0, 0), (2, 1)), AABB(1, (1, 5), (3, 6))],
    ]
    for boxes in cases:
        sp = broadphase.sweep_prune(boxes)
        assert sp.pairs() == broadphase.verify_brute(boxes)


def test_stable_sort_by_id_on_same_start():
    # 同起点必须按编号定序，与传入顺序无关
    boxes = [AABB(2, (0, 0), (1, 1)), AABB(0, (0, 0), (1, 1)),
             AABB(1, (0, 0), (1, 1)), AABB(3, (-1, 0), (0, 1))]
    sp = broadphase.sweep_prune(boxes)
    assert sp.order == (3, 0, 1, 2)
    sp2 = broadphase.sweep_prune(list(reversed(boxes)))
    assert sp2.order == (3, 0, 1, 2)


def test_incremental_matches_full_rebuild():
    boxes = broadphase.load_boxes("data/boxes.json")
    sp = broadphase.sweep_prune(boxes)
    sp.move(2, (0.25, 0.25), (0.75, 0.75))  # 把 2 号移到与 0、1 重叠处
    moved = [AABB(0, (0, 0), (1, 1)), AABB(1, (0.5, 0.5), (2, 2)),
             AABB(2, (0.25, 0.25), (0.75, 0.75))]
    want = broadphase.sweep_prune(moved).pairs()
    assert sp.pairs() == want
    assert sp.pairs() == broadphase.verify_brute(moved)
    # 移回去，结果也要与全量重建一致
    sp.move(2, (5, 5), (6, 6))
    assert sp.pairs() == broadphase.verify_brute(boxes)


def test_scan_counts_prove_incremental():
    boxes = broadphase.load_boxes("data/boxes.json")
    n = len(boxes)
    sp = broadphase.sweep_prune(boxes)
    assert sp.last_sort_scans == n  # 全量构建放置 n 个元素
    sp.move(1, (0.6, 0.6), (2.1, 2.1))
    assert sp.last_sort_scans == 1  # 增量只重插 1 个，不是每帧全排
    assert sp.last_sort_scans < n
    sp.pairs()
    # 扫掠检查次数不超过暴力两两组合数
    assert sp.last_scans <= n * (n - 1) // 2


def test_pruning_reduces_scans():
    # 大量互不相邻的盒子：扫掠检查次数应远小于暴力的 n*(n-1)/2
    boxes = [AABB(i, (i * 10, 0), (i * 10 + 1, 1)) for i in range(20)]
    sp = broadphase.sweep_prune(boxes)
    assert sp.pairs() == []
    assert sp.last_scans < len(boxes) * (len(boxes) - 1) // 2


def test_zero_size_box():
    # 零尺寸盒落在另一个盒内部 -> 是一对
    sp = broadphase.sweep_prune([AABB(0, (0, 0), (2, 2)),
                                 AABB(1, (1, 1), (1, 1))])
    assert sp.pairs() == [(0, 1)]
    # 零尺寸盒落在所有盒之外 -> 无对
    sp2 = broadphase.sweep_prune([AABB(0, (0, 0), (2, 2)),
                                  AABB(1, (5, 5), (5, 5))])
    assert sp2.pairs() == []


def test_coincident_boxes():
    # 完全重合的盒子必须算一对，且结果确定
    boxes = [AABB(0, (0, 0), (1, 1)), AABB(1, (0, 0), (1, 1)),
             AABB(2, (0, 0), (1, 1))]
    sp = broadphase.sweep_prune(boxes)
    assert sp.pairs() == [(0, 1), (0, 2), (1, 2)]
    assert sp.pairs() == broadphase.verify_brute(boxes)


def test_touching_edges_count_as_overlap():
    # 闭区间约定：边界相触算重叠
    sp = broadphase.sweep_prune([AABB(0, (0, 0), (1, 1)),
                                 AABB(1, (1, 0), (2, 1))])
    assert sp.pairs() == [(0, 1)]


def test_deterministic_repeated_runs():
    boxes = broadphase.load_boxes("data/boxes.json")
    sp = broadphase.sweep_prune(boxes)
    first = sp.pairs()
    assert sp.pairs() == first
    sp2 = broadphase.sweep_prune(broadphase.load_boxes("data/boxes.json"))
    assert sp2.pairs() == first
