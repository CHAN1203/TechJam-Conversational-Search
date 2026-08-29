# Clarification Policy Ablation

日期：2026-08-29  
实现 commit：`fa84de2`

## 假设

Conversation State v1 固定根据 profile tag 决定提问顺序，但用户档案偏好不一定是
当前候选商品之间最有区分力的属性。若根据本轮 Top-100 候选中实际出现且有变化的
属性选择问题，应该能更早缩小结果，并提高目标商品的排名。

## 实验设计

Public set 先用 seed `techjam-clarification-v1` 按
`scenario_type / difficulty_bucket` 做确定性分层切分：

| Split | Sessions | Boundary | Browsing | Buying | Intent Override |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 120 | 6 | 48 | 48 | 18 |
| Validation | 80 | 4 | 32 | 32 | 12 |

所有策略使用相同 catalog、retriever、reranker、conversation state 和 evaluator，
唯一变量是 clarification attribute 的选择方式：

- `fixed`：固定 material、size、style、feature、use_case、color 顺序。
- `profile`：优先使用 anonymized profile tags，再回退到固定顺序；这是 E2 基线。
- `candidate`：计算 Top-100 候选中材质、颜色、尺寸、风格、用途、功能的覆盖率与
  多样性，优先询问有实际区分力的属性，再回退到固定顺序。

策略选择只看 validation TechnicalScore；full public metrics 用于历史对比，不用于
决定胜者。这个 validation 是从已发布的 public set 划出的本地 holdout，不等同于
主办方未公开的 800-session private set。

## Validation 结果与决定

| Policy | HitRate@10 | MRR | MTTC ↓ | Efficiency | TechnicalScore | 决定 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Fixed | 0.900 | 0.565526 | 4.475 | 0.6525 | 0.750158 | 淘汰 |
| Profile | 0.900 | 0.527748 | 4.325 | 0.6675 | 0.741824 | 旧基线 |
| Candidate | 0.900 | **0.570734** | **4.275** | **0.6725** | **0.755720** | **保留** |

Candidate 比 profile 的 validation score 高 `0.013896`，比 fixed 高
`0.005562`。三者 HitRate 相同，增益主要来自目标商品排名更前和略早命中。

## Full public set 历史对比

| Policy | HitRate@10 | MRR | MTTC ↓ | Efficiency | TechnicalScore |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed | 0.865 | 0.523492 | 4.640 | 0.6360 | 0.716748 |
| Profile | 0.870 | 0.533748 | 4.565 | 0.6435 | 0.723824 |
| Candidate | **0.870** | **0.544236** | **4.410** | **0.6590** | **0.730071** |

相对 E2 profile，candidate 的 HitRate 持平，MRR `+0.010488`、MTTC
`-0.155` turn、TechnicalScore `+0.006247`。

## 各场景 Full HitRate@10

| Policy | Buying | Browsing | Intent Override | Boundary |
| --- | ---: | ---: | ---: | ---: |
| Fixed | 0.8750 | 0.9625 | 0.566667 | 0.9000 |
| Profile | 0.8875 | 0.9625 | 0.533333 | 1.0000 |
| Candidate | 0.8750 | 0.9625 | **0.600000** | 0.9000 |

Candidate 改善 Intent Override，但在 Buying 和 Boundary 各有小幅回归。因此下一个
实验不应继续扩大通用规则，而应针对 candidate 何时应回退 profile 做开发集分析，
并继续只用 validation 做选择。

## 性能优化

第一次 candidate 完整运行耗时 `144.189s`，profile 为 `82.447s`。原因是每个
候选商品对六种属性重复进行文本拼接和分词。将候选 token set 一次计算并复用后，
candidate 复测为 `88.492s`，所有指标逐项不变；相对 profile 的额外耗时由约 75%
降到约 7%。

## 验证与复现

```powershell
python -m unittest discover -s tests -v
python -m scripts.run_clarification_ablation
python -m scripts.run_clarification_ablation --policies candidate --output reports\experiments\clarification-candidate-optimized.json
python -m evaluator.local_evaluator
```

- 自动测试：21/21 通过。
- 官方 evaluator 默认入口：HitRate@10 `0.870`、MRR `0.544236`、MTTC
  `4.410`、TechnicalScore `0.730071`。
- 原始三策略结果：[clarification-ablation.json](clarification-ablation.json)
- 优化后 candidate 复测：[clarification-candidate-optimized.json](clarification-candidate-optimized.json)

## 限制与下一步

- Validation 只有 80 sessions，Boundary 仅 4 个；小样本差异不能过度解释。
- 当前属性识别使用英文关键词集合，未覆盖同义词、复合属性和否定表达。
- 目前用属性多样性代理 information gain，没有估计用户回答后的真实候选缩减量。
- 下一步优先做 candidate/profile fallback 的开发集错误分析；若没有明确、可测试的
  触发条件，就保留当前简单策略。
