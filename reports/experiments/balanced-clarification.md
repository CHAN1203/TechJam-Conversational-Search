# Balanced Clarification Experiment

日期：2026-08-29  
结果：淘汰，不改变当前 Candidate 策略

## 这次想解决什么

Candidate 策略会观察当前找到的商品，然后询问最能区分这些商品的问题。它整体
表现最好，但在完整 public set 中比旧 Profile 策略少找到一个 Buying 商品和一个
Boundary 商品。

逐个重跑后发现：

- Buying `public_0054`：Candidate 太早询问材质，得到 `Soft Fabric` 这种普通答案，
  正确商品之后反而被挤出前十；Profile 较早询问功能，得到 `Pull On closure` 和
  `Machine Wash`，在第三轮找到商品。
- Boundary `public_0180`：测试用户第一次固定回答“没有偏好”。Candidate 第一个
  问了重要的功能问题，因此浪费了这个机会；Profile 先问材质，第二个才问功能，
  最终在第十轮找到商品。

## 测试的方法

Balanced 策略使用一个简单规则：

> 优先询问用户平时在意、同时又能区分当前商品的属性；没有这种属性时，再使用
> Candidate 原本的商品差异顺序。

例如用户重视风格，而候选商品同时有 casual 和 formal，系统会先问风格。如果所有
商品材质都是 cotton，即使用户平时重视材质，也不会先问材质。

除了提问顺序，其余检索、排序、对话记忆、固定切分和 evaluator 全部不变。

## Validation 决策表

| 方法 | HitRate@10 | MRR | MTTC ↓ | Efficiency | TechnicalScore |
| --- | ---: | ---: | ---: | ---: | ---: |
| Candidate（当前版本） | 0.900 | **0.570734** | 4.275 | 0.67250 | **0.755720** |
| Balanced（新实验） | 0.900 | 0.527748 | **4.2625** | **0.67375** | 0.743074 |

Balanced 虽然平均稍早找到商品，但正确商品的排名明显下降，validation 总分比
Candidate 低 `0.012646`。它没有达到“必须高于 0.755720”的保留条件。

## Full public set 诊断

| 方法 | HitRate@10 | MRR | MTTC ↓ | TechnicalScore |
| --- | ---: | ---: | ---: | ---: |
| Candidate | 0.870 | **0.544236** | **4.410** | **0.730071** |
| Balanced | 0.870 | 0.536248 | 4.540 | 0.725074 |

### 各场景 HitRate@10

| 方法 | Buying | Browsing | Intent Override | Boundary |
| --- | ---: | ---: | ---: | ---: |
| Candidate | 0.8750 | 0.9625 | **0.600000** | 0.9000 |
| Balanced | **0.8875** | 0.9625 | 0.533333 | **1.0000** |

Balanced 的确找回了 Buying 和 Boundary 各一个商品，但同时在 Intent Override 少找
到两个商品。简单来说，它修好了两个看得到的问题，却让其他情况变差。

## 决定

- 淘汰 Balanced，不将它设为默认策略。
- 删除实验行为和只保护该行为的两项测试。
- 保留 Candidate 作为当前版本。
- 保留本报告和原始 JSON，让失败实验可以重现。

## 运行记录

```powershell
python -m unittest discover -s tests -v
python -m scripts.run_clarification_ablation --policies candidate balanced --output reports\experiments\balanced-clarification.json
```

- 实验实现存在时：23/23 tests 通过。
- 删除失败方法后：恢复当前正式的 21-test suite。
- 原始结果：[balanced-clarification.json](balanced-clarification.json)

## 下一步建议

不要继续增加一个全面混合策略。更稳妥的下一步是改善输入文字的处理，例如降低
`fabric / soft fabric` 这类重复、太普通词语对排名的影响。这个问题直接来自失败
案例，而且不需要改变所有场景的提问顺序。
