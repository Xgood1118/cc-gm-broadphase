# 宽相碰撞检测

一个用排序扫掠做宽相、并保证不漏对的碰撞候选生成器。仅使用 Python 标准库。

## 保留签名

- `AABB`
- `sweep_prune`
- `pairs(self)`
- `verify_brute(boxes)`

## 算法与排序规则

- 扫掠轴为第 0 轴（x 轴）。端点排序键为 **(lo_x, id) 升序**：同起点按编号升序定序，排序稳定，与盒子的传入顺序无关，因此同一批盒子两次候选（含顺序）完全一致。
- 扫掠维护活跃集合：进入某盒起点时，先踢出 `hi_x < 当前 lo_x` 的盒子，再与剩余活跃盒子两两组成**疑似对**；疑似对需在全部轴上满足闭区间相交（`lo <= 对方.hi 且 hi >= 对方.lo`）才成为**确认对**（候选对）。
- 闭区间判定使零尺寸盒（`lo == hi`）、贴边接触、完全重合盒都有确定结果；单盒子与空场景候选为空。
- 候选对为规范形 `(小编号, 大编号)`，升序、去重，与 `verify_brute` 暴力比对完全一致（漏报数恒为 0）。

## 增量更新

`update_scene(scene, removed_ids=..., moved=...)` 在有序端点表上做**局部删除 + 二分插入**，从不全量重排：

- `scans`：扫描计数（端点处理 + 插入定位 + 删除过滤），每次调用报告当次增量；
- `sorts`：全量排序次数，构造时恰好 1 次，增量更新恒不增加。

实测（8 个等距盒子）：建场景 `scans=8, sorts=1`；移动 1 盒 `scans=18, sorts=1`；再删 2 盒 `scans=14, sorts=1`——增量代价与场景规模同阶，而非每帧全排。

## 动态场景

- 删除与移动后的候选与"删除后全量重建"完全一致，被删编号不出现在任何候选对。
- `sleep_scene` 标记睡眠：睡眠盒子不参与候选生成；`wake_scene` 唤醒后补齐其与全部唤醒盒子的候选，最终集合与全量一致（点对生成两两独立，按唤醒集过滤与重扫等价）。

## 预算化与统计

- `budgeted_pairs(boxes, budget, cursor=None)`：每处理一个端点消耗 1 单位预算；预算耗尽返回 `done=False` 与 `cursor`，把 `cursor` 传回续算，累计结果等于一次性全量。
- `pair_stats(boxes)` 返回 `dict(suspected, confirmed, missed)`：疑似对数（仅扫掠轴重叠）、确认对数（全轴重叠）、漏报数（暴力有而扫掠无，恒为 0）。

## 自测

```
python -m pytest tests -q
python -m broadphase.cli data/boxes.json --out pairs.json
```

## 验收数值（data/boxes.json，3 盒）

```
python -m pytest tests -q   → 25 passed
python -m broadphase.cli data/boxes.json --out pairs.json
→ boxes=3 pairs=1 suspected=1 confirmed=1 missed=0 scans=3 deterministic=True
```

候选对：`[(0, 1)]`（盒 0 与盒 1 重叠，盒 2 孤立）；漏报 0；两次运行结果一致。
