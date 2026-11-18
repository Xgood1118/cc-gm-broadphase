import argparse
import json

import broadphase as m


def main():
    ap = argparse.ArgumentParser(description="宽相碰撞检测")
    ap.add_argument("boxes", help="盒子 JSON 文件路径")
    ap.add_argument("--out", required=True, help="候选对输出 JSON 路径")
    a = ap.parse_args()

    boxes = m.load_boxes(a.boxes)
    scene = m.build_scene(boxes)
    stats = m.pair_stats(boxes)
    deterministic = m.build_scene(boxes)["pairs"] == scene["pairs"]

    payload = {
        "boxes": len(boxes),
        "pairs": [list(p) for p in scene["pairs"]],
        "suspected": stats["suspected"],
        "confirmed": stats["confirmed"],
        "missed": stats["missed"],
        "scans": scene["scans"],
        "deterministic": deterministic,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(
        "boxes={boxes} pairs={pairs} suspected={suspected} "
        "confirmed={confirmed} missed={missed} scans={scans} "
        "deterministic={deterministic}".format(
            boxes=len(boxes),
            pairs=len(scene["pairs"]),
            suspected=stats["suspected"],
            confirmed=stats["confirmed"],
            missed=stats["missed"],
            scans=scene["scans"],
            deterministic=deterministic,
        )
    )


if __name__ == "__main__":
    main()
