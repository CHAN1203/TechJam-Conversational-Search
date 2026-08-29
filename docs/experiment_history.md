# 实验历史与方法对比矩阵

这份文件是项目的实验总账。每次改变检索、排序、对话状态或提问策略，
都必须在这里追加结果，包括失败实验。这样可以直接回答三个问题：

1. 我们从哪里开始？
2. 每次具体改了什么？
3. 哪个方法最好，为什么保留或淘汰？

> 当前最佳：E9 Slot conflict resolution，Public HitRate@10 `0.895`，
> MRR `0.549056`，MTTC `4.215`，TechnicalScore `0.747917`。

## 1. 方法对比矩阵

所有正式结果都使用完整的 200-session public set、50,000-item frozen
catalog 和未修改的官方 evaluator。`Δ` 表示相对上一项被保留的方法的变化。

| ID | 方法 | 主要变化 | 自动测试 | HitRate@10 | Δ HitRate | MRR | MTTC ↓ | Efficiency | TechnicalScore | Δ Score | 决定 | Commit |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| E0 | Weak BM25 baseline | BM25 直接返回 Top-10；无状态；不提问 | 3 | 0.125 | Reference | 0.068034 | 9.810 | 0.1190 | 0.106710 | Reference | 基线 | `3407835` |
| E1 | Field reranker v1 | BM25 Top-100 后按字段覆盖重新排序 | 10 | 0.160 | +0.035 | 0.076750 | 9.460 | 0.1540 | 0.133825 | +0.027115 | **保留** | `db65ad2` |
| E1-A | Reranker + BM25 rank prior | 在 E1 分数上加入原 BM25 排名先验 | Targeted | 0.155 | -0.005 | 0.073992 | 9.510 | 0.1490 | 0.129498 | -0.004327 | 淘汰 | 未提交 |
| E2 | Conversation State v1 | 累积约束、处理 override、profile 引导且不重复提问 | 14 | 0.870 | +0.710 | 0.533748 | 4.565 | 0.6435 | 0.723824 | +0.589999 | 保留 | `d770b6f` |
| E3-A | Fixed clarification | 固定属性提问顺序 | 21 | 0.865 | -0.005 | 0.523492 | 4.640 | 0.6360 | 0.716748 | -0.007076 | 淘汰 | `fa84de2` |
| E3-B | Profile clarification | E2 的 profile-first 策略，作为消融基准 | 21 | 0.870 | +0.000 | 0.533748 | 4.565 | 0.6435 | 0.723824 | +0.000000 | 旧基线 | `fa84de2` |
| E3-C | Candidate-aware clarification | 优先询问 Top-100 候选中有覆盖且有差异的属性 | 21 | **0.870** | **+0.000** | **0.544236** | **4.410** | **0.6590** | **0.730071** | **+0.006247** | **当前最佳** | `fa84de2` |
| E4 | Always-ask-other probe | 每轮固定询问 `other`，其余逻辑不变；仅作诊断 | 35 | 0.840 | -0.030 | 0.522508 | 3.635 | 0.7365 | 0.724052 | -0.006019 | 淘汰（诊断用） | 未提交 |
| E5 | Slot-aware override memory | override 时保留 category/department slot，其余清除 | 41 | **0.875** | +0.005 | 0.540300 | **4.290** | 0.6710 | **0.733790** | +0.003719 | 保留（证据弱） | 未提交 |
| E6 | Turn-aware override memory | override 时额外保留第 2 轮起通过提问获得的约束 | 48 | 0.875 | +0.000 | 0.540300 | 4.290 | 0.6710 | 0.733790 | +0.000000 | 淘汰（无效果） | 未提交 |
| E7 | Candidate pool 100 -> 500 | 仅放大 BM25 候选池，其余不变 | 51 | 0.875 | +0.000 | 0.528762 | 4.190 | 0.6810 | 0.732329 | -0.001461 | 淘汰 | 未提交 |
| E8-A | Pool-frequency IDF（错误实现） | 用候选池内词频当 IDF | 53 | 0.790 | -0.085 | 0.459067 | 4.975 | 0.6025 | 0.653220 | -0.080570 | 淘汰（推理错误） | 未提交 |
| E8-B | Catalog IDF + pool 500 | fts5vocab 全库 df 加权 | 54 | 0.845 | -0.030 | 0.522619 | 4.625 | 0.6375 | 0.706786 | -0.027004 | 淘汰 | 未提交 |
| E8-C | Catalog IDF + pool 100 | 同上，候选池保持 100 | 54 | 0.860 | -0.015 | 0.540980 | 4.640 | 0.6360 | 0.719494 | -0.014296 | 淘汰 | 未提交 |
| E9 | Slot conflict resolution | gazetteer 每个词只归属一个槽位；pool 100、无 IDF | 53 | **0.895** | +0.020 | **0.549056** | **4.215** | 0.6785 | **0.747917** | **+0.014127** | **当前最佳** | 未提交 |

`E1-A` 的 targeted test 曾完成 red-green，但对应行为因为 evaluator 回归而被
删除，所以它没有进入最终测试套件或 Git commit。失败结果仍然保留在矩阵中。

## 2. 各场景 HitRate@10 矩阵

| 方法 | Buying | Browsing | Intent Override | Boundary |
| --- | ---: | ---: | ---: | ---: |
| E0 Weak BM25 | 0.2375 | 0.0250 | 0.133333 | 0.0000 |
| E1 Field reranker v1 | 0.2375 | 0.0875 | 0.133333 | 0.2000 |
| E1-A + BM25 rank prior | 0.2250 | 0.0875 | 0.133333 | 0.2000 |
| E2 Conversation State v1 | **0.8875** | **0.9625** | **0.533333** | **1.0000** |
| E3-A Fixed clarification | 0.8750 | **0.9625** | 0.566667 | 0.9000 |
| E3-B Profile clarification | **0.8875** | **0.9625** | 0.533333 | **1.0000** |
| E3-C Candidate-aware clarification | 0.8750 | **0.9625** | **0.600000** | 0.9000 |
| E4 Always-ask-other probe | 0.8875 | **0.9625** | 0.333333 | **1.0000** |
| E5 Slot-aware override memory | 0.8750 | **0.9625** | **0.633333** | 0.9000 |
| E6 Turn-aware override memory | 0.8750 | 0.9625 | 0.633333 | 0.9000 |
| E7 Pool 500 | 0.8625 | 0.9500 | 0.700000 | 0.9000 |
| E8-A Pool-frequency IDF | 0.8125 | 0.8250 | 0.600000 | 0.9000 |
| E8-B Catalog IDF + pool 500 | 0.8625 | 0.8875 | 0.666667 | 0.9000 |
| E8-C Catalog IDF + pool 100 | 0.8625 | 0.9000 | **0.733333** | 0.9000 |
| E9 Slot conflict resolution | 0.8750 | **0.9625** | **0.766667** | 0.9000 |

这张表不能单独证明 private-set 表现。它的用途是找出回归发生在哪个场景，
避免总分提升掩盖某一类用户体验变差。

## 3. 前置诊断矩阵

### 3.1 BM25 第一轮候选召回

Candidate Recall 只回答目标有没有进入较大的候选池，不等于最多十轮的官方
HitRate@10。

| 场景 | Sessions | Recall@10 | Recall@50 | Recall@100 | Recall@500 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overall | 200 | 0.185 | 0.380 | 0.525 | 0.860 |
| Buying | 80 | 0.2375 | 0.4750 | 0.5875 | 0.9375 |
| Browsing | 80 | 0.0250 | 0.1875 | 0.3625 | 0.7625 |
| Intent Override | 30 | 0.533333 | 0.666667 | 0.833333 | 0.966667 |
| Boundary | 10 | 0.0000 | 0.3000 | 0.4000 | 0.7000 |

结论：目标从 Top-10 的 37 个增加到 Top-500 的 172 个，主要问题首先是排序，
所以先做 reranker，而不是立刻引入 dense retrieval。

### 3.2 Catalog 字段覆盖率

| 字段 | Coverage | 实验用途 |
| --- | ---: | --- |
| categories | 1.00000 | 主类别与粗粒度意图 |
| title | 0.99996 | 最高权重的商品匹配 |
| details | 0.96660 | 属性与规格约束 |
| store | 0.99372 | 品牌/店铺补充信号 |
| features | 0.89562 | 功能、材质、使用场景 |
| description | 0.52226 | 低权重补充文本 |
| price | 0.21054 | 不适合作为默认硬过滤条件 |

## 4. 按时间记录做过的测试

### T0：官方基线复现

- 日期：2026-08-29
- 方法：未修改的官方 weak BM25 starter。
- 命令：`python -m evaluator.local_evaluator`
- 数据：200 public sessions，50,000 catalog items。
- 结果：HitRate@10 `0.125`，MRR `0.068034`，MTTC `9.81`，
  TechnicalScore `0.106710`。
- 作用：建立所有后续方法的固定比较点。

### T1：BM25 候选召回与 catalog coverage

- 新增 candidate rank、Recall@10/50/100/500 和按场景汇总。
- 新增 catalog 空值/非空值统计。
- 自动测试从 3 个增加到 7 个。
- 命令：

  ```powershell
  python -m scripts.analyze_bm25_recall
  python -m scripts.analyze_catalog
  python -m unittest discover -s tests -v
  ```

- 结论：优先测试 Top-100/500 的轻量 reranking。
- Commits：`583e79c`、`e33c097`、`c51573a`、`c438628`。
- 详细证据：[baseline diagnostic summary](../reports/baseline/diagnostic-summary.md)。

### T2：Field reranker v1

- BM25 候选池从 10 扩到 100。
- 每个 query term 只计算最高价值字段匹配：title `4.0`、categories
  `3.0`、features/details `2.0`、store `1.5`、description `1.0`。
- 分数相同则保留 BM25 原顺序。
- TDD 新增 reranker unit tests 和真实 SQLite FTS5 integration test。
- 自动测试从 7 个增加到 10 个。
- 结果：HitRate@10 `0.160`，TechnicalScore `0.133825`。
- 决定：保留。
- Commit：`db65ad2`。
- 详细证据：[local reranker v1](../reports/experiments/local-reranker-v1.md)。

### T3：BM25 rank prior ablation

- 假设：保留部分 BM25 排名先验可以减少 E1 丢失的 5 个旧命中。
- 改变：为 reranker 加入随 BM25 rank 衰减的 bonus。
- 结果：HitRate@10 `0.155`，TechnicalScore `0.129498`，低于 E1。
- 决定：淘汰；删除对应代码和只保护该失败行为的测试。
- Commit：无。结果记录在 E1 报告与本文件中。

### T4：Conversation State v1

- 跨轮累积有效 query constraints。
- 对明确的 no-preference 回复不加入查询词。
- Intent Override 时清除旧约束。
- 根据 anonymized profile tags 决定 ask_attribute 顺序，且不重复提问。
- 每轮同时返回 clarification question 和 Top-10 recommendations。
- TDD 新增 4 个 conversation behavior tests。
- 自动测试从 10 个增加到 14 个。
- 泄漏检查：`starter/` 不引用 `ground_truth`、`public_set`、`intent_card`
  或 evaluator behavior fields。
- 结果：HitRate@10 `0.870`，TechnicalScore `0.723824`。
- 决定：保留，为当时最佳；后由 E3-C 取代。
- Commit：`d770b6f`。
- 详细证据：[conversation state v1](../reports/experiments/conversation-state-v1.md)。

### T5：独立 worktree 重现

- 从 `d770b6f` 创建 `experiment/clarification-ablation`。
- 使用 hard link 复用同一份 `data/catalog.jsonl`。
- 14/14 tests 通过。
- 完整 evaluator 再次得到 HitRate@10 `0.870`、MRR `0.533748`、
  MTTC `4.565`、TechnicalScore `0.723824`。
- 结论：新实验环境与稳定分支的基线一致，可以开始 clarification ablation。

### T6：固定切分与 Clarification Policy Ablation

- 日期：2026-08-29。
- 用 seed `techjam-clarification-v1` 按 scenario/difficulty 将 public set 固定分为
  120 development sessions 和 80 validation sessions。
- 对比 fixed、profile、candidate 三种策略；其余检索、排序和状态逻辑不变。
- 选择规则：只用 validation TechnicalScore 选胜者。
- Validation score：fixed `0.750158`、profile `0.741824`、candidate
  `0.755720`。
- 决定：candidate 胜出并设为默认；fixed 淘汰，profile 保留为可选 ablation。
- Full public：HitRate@10 `0.870`、MRR `0.544236`、MTTC `4.410`、
  TechnicalScore `0.730071`。
- 实现 commit：`fa84de2`。
- 详细证据：[clarification policy ablation](../reports/experiments/clarification-ablation.md)。

### T7：Candidate 策略性能复测

- 初次完整运行：candidate `144.189s`，profile `82.447s`。
- 优化：每个候选只进行一次文本分词，六种属性复用 token set。
- 优化后 candidate：`88.492s`，全部指标与优化前逐项相同。
- 自动测试增加到 21 个；默认 Agent 走 candidate 策略的行为由 integration test 锁定。
- 官方 evaluator 默认入口复测得到 TechnicalScore `0.730071`。

### T8：Always-ask-other 提问上限诊断

- 日期：2026-08-29
- 假设：本地 simulator 的 `customer_reply` 对 `other` 返回最多两条未披露约束，
  而每个具体属性只返回一条；因此固定询问 `other` 可以测出"提问策略"能带来的
  收益上限。
- 观察到的 evaluator 行为：`classify_constraint` 只会返回 budget、material、
  color、size、style、use_case、feature。`category` 与 `brand` 永远无法匹配，
  询问这两个属性在本地必定得到"没有额外偏好"。
- 改变：新增 `other` clarification policy（固定返回 `other`，忽略 asked 集合）。
  检索、排序、conversation state 全部不变。
- 结果：HitRate@10 `0.840`、MRR `0.522508`、MTTC `3.635`、
  TechnicalScore `0.724052`，低于 E3-C `0.730071`。
- 分场景：buying `0.8875`、browsing `0.9625`、boundary `1.0000` 均持平或略好；
  intent_override 从 `0.600000` 跌到 `0.333333`。
- 机制：`other` 在前两轮就抽干了 intent card 的四条约束，等到第 3/4 轮 override
  到达、状态被清空后，simulator 已无未披露信息可给，session 无法恢复。
- 结论：**提问策略在 buying / browsing / boundary 上已接近饱和**，继续优化
  "问哪个属性"收益很小；真正的瓶颈是 intent_override 的状态处理
  （两种策略的 MTTC 都在 8.5 左右）。
- 决定：淘汰。仅作为诊断保留，不作为提交策略——private simulator 不保证对
  `other` 有相同行为。
- Commit：未提交。
- 详细证据：[clarification-other-probe.json](../reports/experiments/clarification-other-probe.json)

### T9：Slot-aware override memory

- 日期：2026-08-29
- 假设：T8 显示提问策略已饱和，真正瓶颈是 intent_override 的状态处理。
  override 时清空全部约束会连"买什么品类"一起丢掉，应只替换被改写的槽位。
- 改变：
  - 新增 `analysis/gazetteer.py`，从 frozen catalog 挖掘 department / category /
    material / color / style / size 词表，产出 `data/gazetteer.json`（19KB）。
  - 新增 `starter/slots.py`，把用户消息中的词归入槽位，最长匹配优先。
  - `starter/agent.py`：override 时保留 `DURABLE_SLOTS`（category、department），
    除非同一条消息为该槽位给出了替代值；其余槽位清除。
  - gazetteer 文件缺失或损坏时回退为空词表，检索行为与 E3-C 完全一致。
- 词表覆盖率（相对原手写常量）：material `54.7% -> 81.6%`、
  color `33.3% -> 69.5%`、size `20.9% -> 51.0%`、style `36.5% -> 61.1%`。
- 自动测试从 35 增加到 41。既有的
  `test_intent_override_replaces_earlier_constraints` 断言"override 清空全部约束"，
  与本次改动直接冲突，已改写为"丢弃被撤销的值但保留品类"，并通过临时把
  `DURABLE_SLOTS` 置空验证该测试确实会失败（第一版 fixture 无区分力，已修正）。
  既有测试原本隐式依赖 `data/gazetteer.json` 是否存在，现改为在临时目录自带词表。
- 结果：HitRate@10 `0.875`、MRR `0.540300`、MTTC `4.290`、
  TechnicalScore `0.733790`（E3-C 为 `0.730071`，`+0.003719`）。
- 分场景：buying / browsing / boundary 三项完全不变；
  intent_override `0.600000 -> 0.633333`，MTTC `8.500 -> 7.700`。
- 解读：方向正确——唯一变化的场景正是目标场景，且命中率与轮数同时改善。
  但幅度很小：`+0.033333` 在 30 个 intent_override session 上只等于**多命中 1 个**，
  单独不足以证明有效。MRR 反而略降 `-0.003936`。
- 限制与下一步：override 后目前只保留 durable slot，把第 2 轮之后通过提问获得的
  约束一并丢弃，而这些约束并未被用户撤销。下一步应按"来源轮次"保留：
  丢弃第 1 轮的旧偏好与被新消息替换的槽位，保留提问得到的答案。
- Commit：未提交。

### T10：Turn-aware override memory（无效果）

- 日期：2026-08-29
- 假设：E5 在 override 时只保留 durable slot，把第 2 轮起通过提问获得的约束
  一并丢弃，而这些约束并未被用户撤销。按到达轮次保留应能再救回一些 session。
- 改变：slot 记录到达轮次；override 时保留 durable slot 与 `arrived > 1` 的值，
  丢弃第 1 轮自述偏好与被新消息替换的槽位。
- 结果：HitRate@10 `0.875`、MRR `0.540300`、MTTC `4.290`、
  TechnicalScore `0.733790`——**与 E5 逐项完全相同**，四个场景也全部相同。
- 诊断（30 个 intent_override session）：两种规则的保留集合只在 **4 个 session**
  中不同，26 个完全一致；这 4 个的命中与排名均未改变。虽然 23 个 session 确实
  存在"第 2 轮起获得的非 durable 约束"，但它们大多同时被 override 消息命名，
  两种规则都会丢弃。
- 决定：淘汰（无测量效果）。代码保留 turn-aware 版本，因为它更贴合"撤销的是
  开场偏好"的语义，且没有额外成本；但不得声称它带来收益。
- 附带发现：gazetteer 存在跨槽位污染，例如 `small` 同时进入 color 与 size，
  probe 中出现 `'color': {'small': 3}`；`women` 同时进入 department 与 category。
  这是 E5 引入的缺陷，需要在下一步修正。
- 结论：override 的记忆规则不是 intent_override 的瓶颈。两轮迭代累计只带来
  `+0.003719`，应停止在此方向继续调优，转向检索侧（候选池大小、IDF、dense）。
- Commit：未提交。

### T11：Gazetteer 跨槽位污染修正

- 日期：2026-08-29
- 问题：E5 引入的 gazetteer 中有 27 个词同时属于多个槽位，例如 `small` 同时进入
  color 与 size、`women` 同时进入 department 与 category、`hoodie` 同时进入
  category 与 style。probe 中出现 `'color': {'small': 3}`。
- 为什么不能用支持度打破平局：category 的计数来自 taxonomy 节点，attribute 的
  计数来自自由文本覆盖，两者量纲不同；而 `silver` 在 material 与 color 下计数
  完全相同（2935），因为覆盖率是在同一段文本上测的，计数本身不含槽位信息。
- 方案：固定优先级 `department > material > size > category > color > style`，
  按来源可信度排序，每个词只归属最高优先级的槽位。
- 结果：842 个词中跨槽位数量 `27 -> 0`。抽查全部正确：`small -> size`、
  `silver -> material`、`cotton -> material`、`women -> department`、
  `hoodie -> category`、`sneaker -> category`。
- 自动测试增加到 51。

### T12：候选池放大与 IDF 加权（全部淘汰）

- 日期：2026-08-29
- 假设：诊断显示 Recall@100 `0.525`、Recall@500 `0.860`，放大候选池应能提升召回；
  reranker 无 IDF，罕见词与常见词等权，加入 IDF 应能提升排序。
- E7（pool 500）：TechnicalScore `0.732329`，低于 pool 100 的 `0.733790`。
  intent_override 从 `0.633333` 升到 `0.700000`，但 browsing 与 buying 各降一个
  session，MRR 下降 `0.011538`。
- E8-A（错误实现）：用**候选池内**词频计算 IDF，得分暴跌到 `0.653220`。
  原因：候选池是"已经匹配该查询的文档集合"，查询中最关键的词恰恰出现在几乎
  所有候选中，pool-frequency 会把它判为无区分度并降权，信号完全反了。
  IDF 必须在全库上计算。
- E8-B / E8-C（正确实现）：改用 `fts5vocab` 取全库 document frequency，
  pool 500 得 `0.706786`、pool 100 得 `0.719494`，仍然都低于基线 `0.733790`。
- 2x2 对比：

  | | 无 IDF | Catalog IDF |
  | --- | ---: | ---: |
  | pool 100 | **0.733790** | 0.719494 |
  | pool 500 | 0.732329 | 0.706786 |

- 关键观察：两个改动都**提升 intent_override、损害 browsing**。
  intent_override 最好成绩出现在 E8-C 的 `0.733333`（基线 `0.633333`，多命中 3 个），
  但 browsing 从 `0.9625` 跌到 `0.9000`（少命中 5 个）。browsing 有 80 个 session、
  intent_override 只有 30 个，所以总分被 browsing 的损失主导。
- 决定：E7、E8-A/B/C 全部淘汰，恢复 pool 100 且不使用 IDF。
  `rerank_candidates` 保留可选 `idf` 参数（有单元测试），供后续 routing 实验使用。
- 下一步：这组数据支持 **scenario routing**——agent 自己知道 override 何时发生，
  可以只在 override 之后启用 IDF，其余情况保持现状。不预测收益幅度。
- Commit：未提交。

### T13：干净 gazetteer 的独立测量（当前最佳）

- 日期：2026-08-29
- 背景：E5/E6 的分数是在**含跨槽位污染**的 gazetteer 上测的；T11 修好污染后
  一直没有在 pool 100 + 无 IDF 的配置下单独复测。E7/E8 的失败掩盖了这一点。
- 配置：pool 100、无 IDF、干净 gazetteer。相对 E6 唯一的行为差异就是 gazetteer。
- 结果：HitRate@10 `0.895`、MRR `0.549056`、MTTC `4.215`、
  TechnicalScore `0.747917`（E6 为 `0.733790`，`+0.014127`）。
- 分场景：intent_override `0.633333 -> 0.766667`（多命中 4 个），
  browsing `0.9625`、buying `0.8750`、boundary `0.9000` 均未变差。
- 解读：污染本身在破坏 override 逻辑。`small` 被归为 color 时，一次尺寸回答会把
  color 槽标记为"已被替换"，从而丢掉真正的颜色约束；`women` 同时属于 category
  时，一次性别提及会清空品类槽。E5/E6 是在错误的槽位归属之上做更聪明的记忆规则，
  修好数据本身才释放了它们想要的收益。
- 相对 E3-C 基线的累计：TechnicalScore `0.730071 -> 0.747917`（`+0.017846`），
  intent_override `0.600000 -> 0.766667`（多命中 5 个）。
- 限制：仍然只是 200-session public set 的结果，intent_override 只有 30 个 session。
  private set 未验证。
- Commit：未提交。

## 5. 当前自动测试覆盖

| 测试模块 | Tests | 保护的行为 |
| --- | ---: | --- |
| `test_evaluator.py` | 3 | 输出 normalization、miss turn、hidden-field materialization |
| `test_bm25_diagnostics.py` | 3 | rank、cutoff recall、第一轮测量 |
| `test_catalog_profile.py` | 1 | 空 collection 的 coverage 语义 |
| `test_reranker.py` | 2 | 完整约束优先、tie 保持 BM25 顺序 |
| `test_agent_reranking.py` | 1 | Agent 确实 rerank 更大的候选池 |
| `test_conversation_state.py` | 6 | 累积、否定、override、非重复提问、策略选择与默认策略 |
| `test_clarification.py` | 2 | fixed/profile 差异、candidate 的 grounded attribute 选择 |
| `test_clarification_ablation.py` | 1 | 真实 FTS5 evaluator 上的多策略与切分整合 |
| `test_experiment_split.py` | 1 | 固定切分大小、分层平衡、dev/validation 不重叠 |
| `test_experiment_results.py` | 1 | split metrics、scenario metrics 与 TechnicalScore |
| **总计** | **21** | 当前完整回归套件 |

运行完整测试：

```powershell
python -m unittest discover -s tests -v
```

运行官方 public evaluator：

```powershell
python -m evaluator.local_evaluator
```

## 6. 以后如何更新这份文件

每个新方法都执行以下步骤：

1. 分配下一个 ID，例如 `E3`；参数消融使用 `E3-A`、`E3-B`。
2. 在“方法对比矩阵”追加一行，即使结果失败也不能删除。
3. 在“各场景矩阵”追加 Buying、Browsing、Intent Override、Boundary。
4. 在“按时间记录”追加假设、改动、命令、测试数、指标、决定和 commit。
5. 只保留 aggregate metrics；不要把 private labels 或 credentials 写进文档。
6. 若方法被淘汰，写明它比哪个保留方法差，以及差多少。
7. 更新文件顶部的“当前最佳”，但不要覆盖历史结果。

新实验记录模板：

```markdown
### T<N>：<实验名称>

- 日期：YYYY-MM-DD
- 假设：
- 相对上一保留方法的改变：
- 新增或修改的测试：
- 运行命令：
- Overall：HitRate@10、MRR、MTTC、Efficiency、TechnicalScore
- Scenario：Buying、Browsing、Intent Override、Boundary
- 决定：保留 / 淘汰 / 需要更多证据
- Commit：
- 限制与下一步：
```

## 7. 指标解释与比较规则

- HitRate@10：最多 10 轮内找到目标商品的 session 比例，越高越好。
- MRR：命中排名倒数的平均值，越高表示目标更靠前。
- MTTC：首次命中平均轮数；miss 按第 11 轮计算，越低越好。
- Efficiency：`clip((11 - MTTC) / 10, 0, 1)`。
- TechnicalScore：`0.50 × HitRate + 0.30 × MRR + 0.20 × Efficiency`。
- Candidate Recall 与官方 HitRate@10 不可直接比较。
- Public-set 改善不保证 private-set 改善，因此保留失败实验和 ablation 证据。

## 8. 证据来源

- [Official baseline JSON](baseline_results.json)
- [Evaluation configuration](evaluation_config.json)
- [Baseline diagnostics](../reports/baseline/diagnostic-summary.md)
- [Field reranker experiment](../reports/experiments/local-reranker-v1.md)
- [Conversation state experiment](../reports/experiments/conversation-state-v1.md)
- [Clarification policy ablation](../reports/experiments/clarification-ablation.md)
- [Slot memory and retrieval ablation](../reports/experiments/slot-memory-and-retrieval-ablation.md)
- [Adaptive retrieval design](superpowers/specs/2026-08-29-adaptive-intent-aware-retrieval-design.md)
