# 宽相碰撞检测

一个用排序扫掠做宽相、并保证不漏对的碰撞候选生成器

## 保留签名

- `AABB`
- `sweep_prune`
- `pairs(self)`
- `verify_brute(boxes)`

## 自测

```
python -m pytest tests -q
python -m broadphase.cli data/boxes.json --out pairs.json
```
