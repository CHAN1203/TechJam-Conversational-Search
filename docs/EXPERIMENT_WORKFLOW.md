# Experiment Workflow

This is the handoff guide for anyone, including another AI assistant, who
continues this project. Follow it for every change that could affect retrieval,
ranking, conversation memory, clarification questions, or evaluator results.

The goal is simple: change one idea at a time, test it fairly, record every
result, and keep the current best version easy to recover.

## Plain-language glossary

- **Baseline:** the version used as the comparison point.
- **Hypothesis:** the specific reason you think one change will help.
- **Development split:** the sessions used to inspect mistakes and shape an idea.
- **Validation split:** the sessions used only to decide whether the finished
  idea is better. Do not repeatedly tune against these sessions.
- **Ablation:** a fair comparison where one part changes and everything else
  stays the same.
- **Worktree:** a second project folder attached to its own Git branch. It lets
  you test an idea without disturbing the stable version.
- **Regression:** a result that became worse after a change.

## Language and publishing rule

English is the official, Git-tracked version of every report and workflow
document. Chinese translations are for local reading only.

| Document type | English source of truth | Local Chinese mirror |
| --- | --- | --- |
| Experiment ledger | `docs/experiment_history.md` | `docs/zh-CN/experiment_history.md` |
| Workflow | `docs/EXPERIMENT_WORKFLOW.md` | `docs/zh-CN/EXPERIMENT_WORKFLOW.md` |
| Baseline reports | `reports/baseline/*.md` | `reports/zh-CN/baseline/*.md` |
| Experiment reports | `reports/experiments/*.md` | `reports/zh-CN/experiments/*.md` |

The `.gitignore` file excludes both Chinese folders. A fresh GitHub clone will
therefore contain the English documents only. When updating a translation,
keep all metrics, commands, decisions, commit IDs, and limitations identical to
the English source.

Before every commit, confirm that no Chinese mirror is tracked:

```powershell
git check-ignore -v docs/zh-CN/EXPERIMENT_WORKFLOW.md
git check-ignore -v reports/zh-CN/experiments/<report-name>.md
git ls-files docs/zh-CN reports/zh-CN
```

The first two commands should show `.gitignore` rules. The last command should
print nothing.

## Step 1: Start from the stable version

1. Confirm the main worktree is clean and note its current commit.

   ```powershell
   git status --short --branch
   git log -1 --oneline
   ```

2. Create an isolated branch and worktree for one experiment.

   ```powershell
   git worktree add .worktrees/<experiment-name> -b experiment/<experiment-name>
   Set-Location .worktrees/<experiment-name>
   ```

3. Run the full test suite before changing anything.

   ```powershell
   python -m unittest discover -s tests -v
   ```

If the starting tests fail, stop and explain the failure before running the new
experiment. Otherwise, later failures cannot be attributed to the new change.

## Step 2: Write the experiment contract

Before code, add a short draft to the experiment report with:

- one hypothesis;
- one behavior that will change;
- the current retained method used as the baseline;
- a measurable keep/reject threshold;
- tests that will prove the behavior;
- known risks, especially scenario-specific regressions.

Use the fixed split seed `techjam-clarification-v1` for clarification-policy
experiments. Use development sessions to understand errors. Use validation
TechnicalScore to choose the winner. Run the full 200-session public set only
for historical reporting after that choice; do not use it to repeatedly tune
the method.

## Step 3: Implement one idea with tests

Use the red-green-refactor loop:

1. **Red:** add a small test for the intended behavior and confirm it fails for
   the expected reason.
2. **Green:** make the smallest code change that passes the test.
3. **Refactor:** simplify only the code touched by this experiment, then rerun
   the relevant tests.

Do not modify `evaluator/`, public labels, the fixed split, or scoring rules to
make a method look better. Code under `starter/` must not read `ground_truth`,
`public_set`, `intent_card`, or evaluator-only behavior fields.

## Step 4: Run checks in this order

1. Run the new targeted test.
2. Run the full automatic test suite.
3. Run the matching experiment script.
4. Run the official evaluator if the candidate will be compared with the
   current best method.

Common commands:

```powershell
python -m unittest discover -s tests -v
python -m scripts.run_clarification_ablation
python -m scripts.run_clarification_ablation --policies candidate --output reports\experiments\clarification-candidate-optimized.json
python -m evaluator.local_evaluator
```

Record the exact command and raw JSON path. Never type remembered scores into a
report when the JSON output is available.

## Step 5: Update the evidence

Every experiment, including a failed one, must update:

1. the raw result JSON under `reports/`;
2. an English experiment report under `reports/experiments/`;
3. the method and scenario matrix in `docs/experiment_history.md`;
4. the chronological test entry in `docs/experiment_history.md`;
5. the matching local Chinese translation.

Each report must state the hypothesis, what changed, what stayed fixed, split
sizes, test count, all core metrics, scenario HitRate@10, decision, limitations,
reproduction commands, and related commit or review branch.

## Step 6A: If the method is better

1. Keep the implementation and its tests on the experiment branch.
2. Update English evidence and the local Chinese mirror.
3. Run all verification checks again.
4. Commit named files only; do not use `git add .` or `git add -A`.
5. Push the experiment branch.
6. Ask the project owner whether to merge locally, open a pull request, or keep
   the branch for more review.
7. After an approved merge, rerun the full tests on the merged version.

## Step 6B: If the method is worse

A rejected result is still useful evidence. Preserve it without making it the
production default.

1. Keep the exact experimental code and tests on a branch named
   `review/<experiment-name>-implementation`.
2. Add a short cross-check guide explaining the intended behavior, commands,
   observed scores, and files another AI should inspect.
3. Run the exact experiment and full tests on that review branch.
4. Commit and push the review branch so another AI can check whether poor
   results came from an implementation mistake.
5. On the stable experiment branch, remove the rejected behavior while keeping
   the English report, raw metrics, and matrix row.
6. Keep the review worktree until the owner decides it is no longer needed.

Ask the reviewer to classify findings as one of these:

- **Implementation bug:** the code does not match the intended rule.
- **Test gap:** important behavior is not protected by a test.
- **Design weakness:** the code matches the rule, but the rule performs poorly.
- **Evaluator concern:** the experiment or comparison is not fair or reproducible.

Do not conclude that the idea itself failed until the implementation and
evaluation setup have been cross-checked.

## Step 7: Final verification before a commit

Run fresh checks on the exact files being committed:

```powershell
python -m unittest discover -s tests -v
git diff --check
git status --short --ignored
git ls-files docs/zh-CN reports/zh-CN
```

Also check Markdown links and scan the staged diff for credentials, private
labels, user data, and evaluator-only information. Stage English files by name.
After staging, run `git diff --cached --stat` and `git diff --cached` before the
commit.

## Experiment record template

```markdown
### T<N>: <Experiment name>

- Date: YYYY-MM-DD
- Hypothesis:
- Change from the last retained method:
- New or changed tests:
- Commands:
- Overall: HitRate@10, MRR, MTTC, Efficiency, TechnicalScore
- Scenarios: Buying, Browsing, Intent Override, Boundary
- Decision: Keep / Reject / Need more evidence
- Commit or review branch:
- Limitations and next step:
```

## Handoff checklist for another AI

Start by reading, in order:

1. `README.md`
2. `docs/EXPERIMENT_WORKFLOW.md`
3. `docs/experiment_history.md`
4. the report for the current best experiment
5. the latest rejected experiment report and its review guide, if one exists

Then run `git status --short --branch`, `git worktree list`, and the full test
suite. Explain technical terms in plain language when reporting to the project
owner. Lead with what changed and whether the score improved; put implementation
details after that.
