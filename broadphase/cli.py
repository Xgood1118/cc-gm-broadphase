# -*- coding: utf-8 -*-
import argparse
import json

import broadphase as m


def main():
    ap = argparse.ArgumentParser(description="宽相碰撞检测")
    ap.add_argument("input", help="盒子 JSON 文件，如 data/boxes.json")
    ap.add_argument("--out", required=True, help="候选对与统计输出 JSON")
    a = ap.parse_args()

    boxes = m.load_boxes(a.input)
    sp = m.sweep_prune(boxes)
    cand = sp.pairs()
    brute = m.verify_brute(boxes)
    depth = m.max_overlap_depth(boxes)
    stats = {
        "boxes": len(boxes),
        "candidate_pairs": len(cand),
        "brute_pairs": len(brute),
        "scans": sp.last_scans,
        "max_overlap_pairs": depth * (depth - 1) // 2,
        "match_brute": cand == brute,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"pairs": [list(p) for p in cand], "stats": stats},
                  f, ensure_ascii=False, indent=2)
    for k, v in stats.items():
        print("%s: %s" % (k, v))


if __name__ == "__main__":
    main()
