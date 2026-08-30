# Session Viewer

A local page for replaying one public-set session turn by turn against the
current agent. Type a sample number, watch the conversation, the ranked list,
the agent's slot state and the hidden intent card advance together.

This is a development tool. It is not part of the submitted agent and must not
be included in a submission bundle.

## Run it

Two processes, from the repository root:

```powershell
python -m frontend.server.app
npm --prefix frontend install
npm --prefix frontend run dev
```

Then open <http://localhost:5173> and type a number from 1 to 200.

The API takes about six seconds to start while it indexes the 50,000-product
catalog. After that a session runs in well under a second.

Keyboard: `<-` and `->` step through turns, `space` plays and pauses. Clicking
a cell in the turn ribbon or an exchange in the conversation jumps to it.

## Which agent it runs

`SessionRunner` constructs `Agent(catalog_path)` with no overrides, so the
viewer always runs whatever the current defaults are — today that is E16, the
best entry in `docs/experiment_history.md` (constraint ledger, information-gain
probe at threshold 1, implicit-rejection weight 1.0, candidate clarification
policy, candidate pool 100, no IDF, cleaned gazetteer). Change the defaults and the
viewer follows without any edit here.

The header shows the live configuration so you can confirm what ran.

## How the transcript is captured

`docs/submission_rules.md` forbids modifying evaluator files, so nothing here
instruments `evaluate()`.

Instead `RecordingAgent` wraps the real agent and logs each `reset`/`respond`
as the **unmodified** `evaluate()` drives it. The turns you watch are the turns
a scoring run produces — there is no second implementation of the turn loop
that could drift.

Two things in the UI are not direct observations, and are labelled as such:

- **Disclosed constraints** are reconstructed by matching intent-card text
  against the customer's messages. The evaluator keeps that set as a local
  variable that cannot be read from outside.
- **Agent state** is read from private attributes (`_session_slots`,
  `_session_terms`). If `Agent` is refactored, that panel goes blank rather
  than breaking the viewer.

## API

| Route | Purpose |
| --- | --- |
| `GET /api/health` | sample count and live agent configuration |
| `GET /api/samples` | index, id, scenario and difficulty for all 200 samples |
| `POST /api/run` | body `{"sample": 190}` — returns the full transcript |

The server is single-threaded and binds `127.0.0.1` only. Single-threaded is
deliberate: the agent's SQLite connection uses the default
`check_same_thread=True`, so a threading server would fail on the second
request.

## Tests

```powershell
python -m unittest tests.test_session_viewer -v
```

The load-bearing test is `test_recording_does_not_change_evaluator_metrics`:
it asserts that `evaluate()` returns identical sessions with and without the
recording proxy, which is what makes it safe to trust the replay.
