# -*- coding: utf-8 -*-
"""宽相碰撞检测"""

from dataclasses import dataclass


@dataclass
class AABB:
    """包围盒。"""
    id: int
    lo: tuple
    hi: tuple


def pairs(self):
    """生成候选对"""
    raise NotImplementedError("pairs 尚未实现")


def verify_brute(boxes):
    """暴力比对"""
    raise NotImplementedError("verify_brute 尚未实现")


def load_boxes(path):
    """读入与落盘辅助"""
    raise NotImplementedError("load_boxes 尚未实现")


class sweep_prune:
    """class"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("sweep_prune 尚未实现")

