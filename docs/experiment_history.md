# 实验历史与方法对比矩阵

这份文件是项目的实验总账。每次改变检索、排序、对话状态或提问策略，
都必须在这里追加结果，包括失败实验。这样可以直接回答三个问题：

1. 我们从哪里开始？
2. 每次具体改了什么？
3. 哪个方法最好，为什么保留或淘汰？

> 当前最佳：Conversation State v1，Public HitRate@10 `0.870`，
> MRR `0.533748`，MTTC `4.565`，TechnicalScore `0.723824`。

## 1. 方法对比矩阵

所有正式结果都使用完整的 200-session public set、50,000-item frozen
catalog 和未修改的官方 evaluator。`Δ` 表示相对上一项被保留的方法的变化。

| ID | 方法 | 主要变化 | 自动测试 | HitRate@10 | Δ HitRate | MRR | MTTC ↓ | Efficiency | TechnicalScore | Δ Score | 决定 | Commit |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| E0 | Weak BM25 baseline | BM25 直接返回 Top-10；无状态；不提问 | 3 | 0.125 | Reference | 0.068034 | 9.810 | 0.1190 | 0.106710 | Reference | 基线 | `3407835` |
| E1 | Field reranker v1 | BM25 Top-100 后按字段覆盖重新排序 | 10 | 0.160 | +0.035 | 0.076750 | 9.460 | 0.1540 | 0.133825 | +0.027115 | **保留** | `db65ad2` |
| E1-A | Reranker + BM25 rank prior | 在 E1 分数上加入原 BM25 排名先验 | Targeted | 0.155 | -0.005 | 0.073992 | 9.510 | 0.1490 | 0.129498 | -0.004327 | 淘汰 | 未提交 |
| E2 | Conversation State v1 | 累积约束、处理 override、profile 引导且不重复提问 | 14 | **0.870** | **+0.710** | **0.533748** | **4.565** | **0.6435** | **0.723824** | **+0.589999** | **当前最佳** | `d770b6f` |

`E1-A` 的 targeted test 曾完成 red-green，但对应行为因为 evaluator 回归而被
删除，所以它没有进入最终测试套件或 Git commit。失败结果仍然保留在矩阵中。

## 2. 各场景 HitRate@10 矩阵

| 方法 | Buying | Browsing | Intent Override | Boundary |
| --- | ---: | ---: | ---: | ---: |
| E0 Weak BM25 | 0.2375 | 0.0250 | 0.133333 | 0.0000 |
| E1 Field reranker v1 | 0.2375 | 0.0875 | 0.133333 | 0.2000 |
| E1-A + BM25 rank prior | 0.2250 | 0.0875 | 0.133333 | 0.2000 |
| E2 Conversation State v1 | **0.8875** | **0.9625** | **0.533333** | **1.0000** |

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
- 决定：保留，为当前最佳。
- Commit：`d770b6f`。
- 详细证据：[conversation state v1](../reports/experiments/conversation-state-v1.md)。

### T5：独立 worktree 重现

- 从 `d770b6f` 创建 `experiment/clarification-ablation`。
- 使用 hard link 复用同一份 `data/catalog.jsonl`。
- 14/14 tests 通过。
- 完整 evaluator 再次得到 HitRate@10 `0.870`、MRR `0.533748`、
  MTTC `4.565`、TechnicalScore `0.723824`。
- 结论：新实验环境与稳定分支的基线一致，可以开始 clarification ablation。

## 5. 当前自动测试覆盖

| 测试模块 | Tests | 保护的行为 |
| --- | ---: | --- |
| `test_evaluator.py` | 3 | 输出 normalization、miss turn、hidden-field materialization |
| `test_bm25_diagnostics.py` | 3 | rank、cutoff recall、第一轮测量 |
| `test_catalog_profile.py` | 1 | 空 collection 的 coverage 语义 |
| `test_reranker.py` | 2 | 完整约束优先、tie 保持 BM25 顺序 |
| `test_agent_reranking.py` | 1 | Agent 确实 rerank 更大的候选池 |
| `test_conversation_state.py` | 4 | 累积、否定、override、非重复提问 |
| **总计** | **14** | 当前完整回归套件 |

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
- [Adaptive retrieval design](superpowers/specs/2026-08-29-adaptive-intent-aware-retrieval-design.md)
