# -*- coding: utf-8 -*-
"""宽相碰撞检测：排序扫掠（sweep and prune）。

约定：
- 扫掠轴为第 0 轴（x 轴），端点排序键为 (lo_x, id)，升序、稳定，
  同起点按编号升序定序。
- 重叠判定为闭区间相交（lo <= 对方.hi 且 hi >= 对方.lo），
  因此零尺寸盒、完全重合盒都有确定结果。
- 候选对（确认对）必须在所有轴上重叠；仅在扫掠轴上重叠的计入疑似对。
"""

import json
from bisect import bisect_left
from dataclasses import dataclass

__all__ = [
    "AABB",
    "sweep_prune",
    "verify_brute",
    "load_boxes",
    "build_scene",
    "update_scene",
    "sleep_scene",
    "wake_scene",
    "budgeted_pairs",
    "pair_stats",
]


@dataclass
class AABB:
    """包围盒。"""
    id: int
    lo: tuple
    hi: tuple

    def __post_init__(self):
        self.lo = tuple(self.lo)
        self.hi = tuple(self.hi)


def _canon(a, b):
    """候选对规范形：小编号在前。"""
    return (a, b) if a < b else (b, a)


def _overlap(a, b):
    """闭区间全轴重叠判定（含零尺寸与贴边接触）。"""
    return all(
        a.lo[k] <= b.hi[k] and b.lo[k] <= a.hi[k]
        for k in range(min(len(a.lo), len(b.lo)))
    )


class sweep_prune:
    """沿 x 轴的排序扫掠宽相。

    属性:
        scans: 累计扫描计数（端点处理 + 增量插入定位 + 删除过滤），
               用于证明增量更新不是每帧全排。
        sorts: 全量排序次数（构造时恰好 1 次，增量更新不增加）。
    """

    def __init__(self, boxes=()):
        self._by_id = {b.id: b for b in boxes}
        self._sorted = sorted((b.lo[0], b.id) for b in self._by_id.values())
        self._pairs = []
        self._suspected = 0
        self.scans = 0
        self.sorts = 1
        self._resweep()

    def _resweep(self):
        """对当前有序端点表做一次 O(n) 扫掠，重建疑似/确认对。"""
        self._pairs = []
        self._suspected = 0
        active = []
        for x, bid in self._sorted:
            b = self._by_id[bid]
            active = [i for i in active if self._by_id[i].hi[0] >= x]
            self.scans += 1
            for i in active:
                self._suspected += 1
                if _overlap(b, self._by_id[i]):
                    self._pairs.append(_canon(i, bid))
            active.append(bid)
        self._pairs = sorted(set(self._pairs))

    def pairs(self):
        """生成候选对：与暴力比对完全一致的确认对列表（升序、去重）。"""
        return list(self._pairs)

    @property
    def suspected(self):
        """疑似对数（仅扫掠轴重叠）。"""
        return self._suspected

    def update(self, removed_ids=(), moved=()):
        """增量更新：局部删除 + 二分插入，不做全量排序。

        返回本次更新的扫描次数。
        """
        before = self.scans
        moved = list(moved or [])
        drop = set(removed_ids or ()) | {b.id for b in moved}
        if drop:
            self.scans += len(self._sorted)  # 删除过滤扫描
            self._sorted = [e for e in self._sorted if e[1] not in drop]
            for i in drop:
                self._by_id.pop(i, None)
        for b in moved:
            self._by_id[b.id] = b
            pos = bisect_left(self._sorted, (b.lo[0], b.id))
            self._sorted.insert(pos, (b.lo[0], b.id))
            self.scans += pos + 1  # 插入定位扫描
        self._resweep()
        return self.scans - before


def verify_brute(boxes):
    """暴力比对：全轴重叠的所有无序对，规范形升序。"""
    bs = list(boxes)
    out = set()
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            if _overlap(bs[i], bs[j]):
                out.add(_canon(bs[i].id, bs[j].id))
    return sorted(out)


def load_boxes(path):
    """读入盒子 JSON（[{id, lo, hi}, ...]）为 AABB 列表。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [AABB(d["id"], tuple(d["lo"]), tuple(d["hi"])) for d in data]


def _awake_pairs(sp, sleeping):
    """全量候选按唤醒集过滤（与只对唤醒盒子重扫等价）。"""
    if not sleeping:
        return sp.pairs()
    return [p for p in sp.pairs() if p[0] not in sleeping and p[1] not in sleeping]


def build_scene(boxes):
    """建立场景：返回 dict(boxes=[盒子列表], pairs=[(id_a, id_b), ...])。"""
    sp = sweep_prune(boxes)
    return {
        "boxes": list(boxes),
        "pairs": sp.pairs(),
        "sleeping": set(),
        "scans": sp.scans,
        "sorts": sp.sorts,
        "_sp": sp,
    }


def update_scene(scene, removed_ids=None, moved=None):
    """删除与移动后增量更新：返回与 build_scene 同结构的 dict。

    结果中的 pairs 与"删除后全量重建"完全一致；scans 为本次增量
    更新的扫描次数，sorts 不增加（证明未全量重排）。
    """
    sp = scene["_sp"]
    removed = set(removed_ids or ())
    moved = list(moved or [])
    moved_by_id = {b.id: b for b in moved}
    delta = sp.update(removed_ids=removed, moved=moved)
    boxes = [moved_by_id.get(b.id, b) for b in scene["boxes"] if b.id not in removed]
    sleeping = {i for i in scene.get("sleeping", set()) if i not in removed}
    return {
        "boxes": boxes,
        "pairs": _awake_pairs(sp, sleeping),
        "sleeping": sleeping,
        "scans": delta,
        "sorts": sp.sorts,
        "_sp": sp,
    }


def sleep_scene(scene, sleeping_ids):
    """标记睡眠：返回 dict(pairs)，睡眠盒子不得出现在候选对。"""
    sleeping = set(scene.get("sleeping", set())) | set(sleeping_ids or ())
    sp = scene["_sp"]
    return {
        "boxes": list(scene["boxes"]),
        "pairs": _awake_pairs(sp, sleeping),
        "sleeping": sleeping,
        "scans": 0,
        "sorts": sp.sorts,
        "_sp": sp,
    }


def wake_scene(scene, ids):
    """唤醒：返回 dict(pairs)，必须等于对全部唤醒盒子重新求候选。"""
    sleeping = set(scene.get("sleeping", set())) - set(ids or ())
    sp = scene["_sp"]
    return {
        "boxes": list(scene["boxes"]),
        "pairs": _awake_pairs(sp, sleeping),
        "sleeping": sleeping,
        "scans": 0,
        "sorts": sp.sorts,
        "_sp": sp,
    }


def budgeted_pairs(boxes, budget, cursor=None):
    """预算化候选：每处理一个端点消耗 1 单位预算。

    预算不足时返回 dict(done=False, cursor=...)，把 cursor 传回即可
    续算；多次调用的累计 pairs 等于一次性全量结果。
    """
    boxes = list(boxes)
    order = sorted((b.lo[0], b.id) for b in boxes)
    by_id = {b.id: b for b in boxes}
    if cursor is None:
        i, active = 0, []
    else:
        i, active = cursor["i"], list(cursor["active"])
    found = []
    steps = 0
    while i < len(order) and steps < budget:
        x, bid = order[i]
        b = by_id[bid]
        active = [a for a in active if by_id[a].hi[0] >= x]
        for a in active:
            if _overlap(b, by_id[a]):
                found.append(_canon(a, bid))
        active.append(bid)
        i += 1
        steps += 1
    done = i >= len(order)
    return {
        "pairs": sorted(set(found)),
        "done": done,
        "cursor": None if done else {"i": i, "active": active},
        "scans": steps,
    }


def pair_stats(boxes):
    """返回 dict(suspected, confirmed, missed)，漏报数必须为 0。"""
    boxes = list(boxes)
    sp = sweep_prune(boxes)
    confirmed = sp.pairs()
    missed = len(set(verify_brute(boxes)) - set(confirmed))
    return {
        "suspected": sp.suspected,
        "confirmed": len(confirmed),
        "missed": missed,
    }
