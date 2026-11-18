# -*- coding: utf-8 -*-
"""宽相碰撞检测"""

from dataclasses import dataclass


@dataclass
class AABB:
    """包围盒。"""
    id: int
    lo: tuple
    hi: tuple


def AABB:
    """class"""
    raise NotImplementedError("AABB 尚未实现")


def sweep_prune:
    """class"""
    raise NotImplementedError("sweep_prune 尚未实现")


def pairs(self):
    """生成候选对"""
    raise NotImplementedError("pairs 尚未实现")


def verify_brute(boxes):
    """暴力比对"""
    raise NotImplementedError("verify_brute 尚未实现")


def load_boxes(path):
    """读入与落盘辅助"""
    raise NotImplementedError("load_boxes 尚未实现")



def build_scene(boxes):
    """建立场景：返回 dict(boxes=[盒子列表], pairs=[(id_a, id_b), ...])。"""
    raise NotImplementedError("build_scene 尚未实现")


def update_scene(scene, removed_ids=None, moved=None):
    """删除与移动后增量更新：返回与 build_scene 同结构的 dict。"""
    raise NotImplementedError("update_scene 尚未实现")


def sleep_scene(scene, sleeping_ids):
    """标记睡眠：返回 dict(pairs)，睡眠盒子不得出现在候选对。"""
    raise NotImplementedError("sleep_scene 尚未实现")


def wake_scene(scene, ids):
    """唤醒：返回 dict(pairs)，必须等于对全部盒子重新求候选。"""
    raise NotImplementedError("wake_scene 尚未实现")


def budgeted_pairs(boxes, budget, cursor=None):
    """预算化候选：返回 dict(pairs, done, cursor)。"""
    raise NotImplementedError("budgeted_pairs 尚未实现")


def pair_stats(boxes):
    """返回 dict(suspected, confirmed, missed)。"""
    raise NotImplementedError("pair_stats 尚未实现")
