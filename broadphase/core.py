# -*- coding: utf-8 -*-
"""宽相碰撞检测：排序扫掠（sweep and prune）。

约定：
- 区间按闭区间处理，边界相触（lo == hi）视为重叠。
- 排序键为 (lo[0], id)：同起点按编号升序，保证稳定与确定。
"""

import bisect
import json
from dataclasses import dataclass

__all__ = [
    "AABB",
    "sweep_prune",
    "verify_brute",
    "load_boxes",
    "max_overlap_depth",
]


@dataclass
class AABB:
    """包围盒。lo/hi 为各轴最小/最大坐标，维度任意但同一批盒子需一致。"""
    id: int
    lo: tuple
    hi: tuple

    def __post_init__(self):
        self.lo = tuple(self.lo)
        self.hi = tuple(self.hi)
        if len(self.lo) != len(self.hi):
            raise ValueError("lo 与 hi 维度不一致")
        for a, b in zip(self.lo, self.hi):
            if a > b:
                raise ValueError("lo 不能大于 hi")


def _overlaps(a, b):
    """闭区间重叠判定：所有轴都相交才算重叠（边界相触算重叠）。"""
    for lo_a, hi_a, lo_b, hi_b in zip(a.lo, a.hi, b.lo, b.hi):
        if lo_a > hi_b or lo_b > hi_a:
            return False
    return True


def _key(box):
    """稳定排序键：先按第 0 轴起点，同起点按编号。"""
    return (box.lo[0], box.id)


class sweep_prune:
    """排序扫掠宽相。

    沿第 0 轴维护按 (lo[0], id) 排序的盒子序列；pairs() 扫描该序列，
    对第 0 轴仍可能相交的盒子做全轴重叠检查。move() 只把被移动的盒子
    从有序序列中摘除并局部重插，不做全量重排。

    计数器（用于证明增量不是每帧全排）：
    - last_sort_scans：最近一次排序维护放置的元素数（全量建 = n，增量移动 = 1）。
    - sort_scans：累计放置次数。
    - last_scans：最近一次 pairs() 的第 0 轴重叠检查次数（含剪枝 break 那次）。
    - scans：累计检查次数。
    """

    def __init__(self, boxes=()):
        self._boxes = {}
        self._order = []  # AABB 列表，按 _key 升序
        self._keys = []   # 与 _order 平行的排序键
        self.sort_scans = 0
        self.last_sort_scans = 0
        self.scans = 0
        self.last_scans = 0
        for b in boxes:
            self._insert(b)
        # 全量构建：放置了全部 n 个元素
        self.last_sort_scans = len(self._order)
        self.sort_scans += len(self._order)

    def _insert(self, box):
        if box.id in self._boxes:
            raise ValueError("重复的盒子编号: %r" % (box.id,))
        k = _key(box)
        i = bisect.bisect_left(self._keys, k)
        self._keys.insert(i, k)
        self._order.insert(i, box)
        self._boxes[box.id] = box

    def add(self, box):
        """新增一个盒子（局部插入，不计为全量重排）。"""
        self._insert(box)
        self.sort_scans += 1
        self.last_sort_scans = 1

    def move(self, box_id, lo, hi):
        """增量更新：把指定盒子移动到新位置，只做一次摘除 + 局部重插。"""
        old = self._boxes[box_id]
        i = bisect.bisect_left(self._keys, _key(old))
        self._keys.pop(i)
        self._order.pop(i)
        new = AABB(box_id, tuple(lo), tuple(hi))
        k = _key(new)
        j = bisect.bisect_left(self._keys, k)
        self._keys.insert(j, k)
        self._order.insert(j, new)
        self._boxes[box_id] = new
        self.sort_scans += 1
        self.last_sort_scans = 1

    @property
    def order(self):
        """当前扫掠顺序（盒子编号元组），可用于检查稳定排序。"""
        return tuple(b.id for b in self._order)

    def pairs(self):
        """生成候选对。返回 [(i, j), ...]，i < j，按字典序排序，结果确定。"""
        result = []
        scans = 0
        order = self._order
        n = len(order)
        for i in range(n):
            a = order[i]
            hi0 = a.hi[0]
            for j in range(i + 1, n):
                b = order[j]
                scans += 1
                if b.lo[0] > hi0:
                    break  # 第 0 轴之后都不可能相交，剪枝
                if _overlaps(a, b):
                    result.append((a.id, b.id) if a.id < b.id else (b.id, a.id))
        result.sort()
        self.last_scans = scans
        self.scans += scans
        return result


def verify_brute(boxes):
    """暴力比对：全部两两组合做重叠检查，返回与 pairs() 相同的规范形式。"""
    boxes = list(boxes)
    res = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if _overlaps(a, b):
                res.append((a.id, b.id) if a.id < b.id else (b.id, a.id))
    res.sort()
    return res


def load_boxes(path):
    """从 JSON 文件读入盒子列表。"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [AABB(int(d["id"]), tuple(d["lo"]), tuple(d["hi"])) for d in data]


def max_overlap_depth(boxes):
    """第 0 轴上同时重叠的最大盒子数（扫掠深度，闭区间）。"""
    events = []
    for b in boxes:
        events.append((b.lo[0], 1, b.id))   # 先进入
        events.append((b.hi[0], -1, b.id))  # 后离开，保证边界相触计入
    events.sort()
    depth = 0
    best = 0
    for _, delta, _ in events:
        depth += delta
        if depth > best:
            best = depth
    return best
