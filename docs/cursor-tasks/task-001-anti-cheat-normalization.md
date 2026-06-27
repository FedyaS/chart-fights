# Cursor Agent Task: Anti-Cheat, Normalization, and Determinism Verification (MVP)

**Context**: Chart-Fights. References:
- docs/design/architecture-overview.md (anti-cheat section)
- docs/design/game-mechanics-spec.md (normalization P[0]=100, private arenas, generic labels)
- docs/design/roadmap-and-open-questions.md

**Goal**: Implement mechanisms for normalization, private arena handling, and determinism verification to ensure fairness and prevent external knowledge cheating in matches.

## Requirements (from specs + arch)
- For every match: reset all instrument series so first price = 100.00, use % returns only.
- Instrument labels generic during match (e.g. "Broad Equities"), real names optional post-match.
- Arena selection from pre-loaded private slices (server-side, not client).
- Determinism: same arena + action sequence must produce identical state/P&L for all players.
- Verification: unit tests or harness that replays action log and asserts identical outcomes.
- Logging: full action + arena ID for post-match re-sim or validation.
- Support mystery/randomized start dates if needed for extra anti-cheat.

**Non-goals**: Intraday, live data, real-money, full tournaments (MVP 1v1).

## Acceptance Criteria
1. Normalization function that takes raw OHLC slice and returns normalized to 100 with % deltas.
2. Arena loader that enforces private slices and generic labels.
3. Determinism test: replay same actions on same arena, assert bit-identical state for multiple "players".
4. Action logging sufficient for re-simulation.
5. Integration note for simulation engine to use normalized data.
6. Docs in README or inline explaining anti-cheat approach.

## Suggested Approach / Files to Touch or Create
- `data/normalization.py` or similar for the reset logic.
- Extend arena loader in data pipeline.
- `tests/test_determinism.py` or in existing test_replay.
- Update sim engine to log actions with arena ID.
- Reference in handoff and arch.

## Cursor Agent Prompt to Use (copy this)
"Implement anti-cheat, normalization, and determinism verification for Chart-Fights per docs/cursor-tasks/task-001-anti-cheat-normalization.md and references in docs/design/architecture-overview.md (anti-cheat), game-mechanics-spec.md (normalization section), roadmap-and-open-questions.md.

Create normalization to P[0]=100 using % returns, generic labels during play, private arena enforcement, action logging for re-sim, and tests asserting identical outcomes across players for same inputs. Follow exact rules from specs. No UI or full app code.

Reference research in docs/research/ for data. Ask only for hard blockers."

## Integration Notes
- Depends on data pipeline (task-006) for arenas.
- Used by backend sim (005) and frontend.
- Key for fairness per vision.

**Priority**: High — core to anti-cheat and MVP validity.
**Estimated size**: Small for MVP.
**Owner**: Coding agent (Cursor or other).

**Harness, Replay Verification & Testing Insights (from det/GGPO/Photon sub + anti-cheat notes)**
High-value integration for determinism (ties roadmap Tier1 OQ "prove determinism... lag sim on clock contention"):
- Patterns: Server-authoritative (clients actions-only). Log actions (real_ts + sim_t + player + type + payload). Arena + log = seed for verify_replay (re-init engine, replay sorted log, assert final equity/hash match reported).
- GGPO/Photon/Bevy: Synctest harness (multi-engine identical actions + periodic checksum match). Lag injection on action queue for TB contention (Pause override vs FF max+all-pay). Periodic Decimal state hashes (T/R/equities/positions/TB, sorted, quantized).
- Python harness recs: `tests/test_determinism.py` (load arena, N engines, feed same seq or fuzzed, assert hash/equity identical; property-based with hypothesis). `verify_replay(arena_id, log)` returns final state + hash. Lag/contention tests. Cross-env CI.
- Pitfalls (bar sim): Float -> always Decimal + quantize for P&L/equity/TB/R; consistent op order (TB resolve before advance, sorted simultaneous actions); stable hash (SHA sorted keys, no platform hash()); arena hash for norm data.
- Pseudocode (from sub): SimulationEngine with arena (norm bars), T/R, log, compute_state_hash (Decimal quantize), verify_replay (fresh eng + replay actions). TempoBarResolver exact per spec.
- Integration: Task-006 provides norm arena + hash. Task-005 uses in sim loop (log on receive, advance with TB, periodic cs, post-match verify). Update anti-cheat-determinism-design-notes.md if new.
- AC extension note: Add harness tests, verify_replay hook, lag sim for contention. Reference full sub output in STATUS + design notes.
- Cursor prompt addition: "Include harness (synctest, lag injection for TB, verify_replay) + Decimal hashes per anti-cheat notes and det sub. Tests assert bit-identical + contention cases."

**Sources/Refs**: det sub (GGPO/Photon pseudocode/harness/2026 updates), anti-cheat-determinism-design-notes.md (full details), roadmap OQs, task-005 ACs.

Start by reading the referenced specs and manifest.

---

## Deep Research Resolutions (sibling worker, 2026-06-26)

This section resolves the **determinism-proof / anti-cheat** open questions, grounded in 2026 best practices (GGPO SyncTest semantics, deterministic hashing of Python objects, property-based testing). It **extends** the harness notes above and `anti-cheat-determinism-design-notes.md` rather than duplicating them. MVP scope: in-memory single process, wall-time base, server-authoritative. The clock/TB/reconnect engine decisions live in **task-005 R1–R6** — this file owns *how we prove the engine is deterministic and tamper-evident*.

### R1. The determinism contract: canonical state = pure function of (arena, sorted action log)

**Resolution — the audited canonical state is defined as a pure, side-effect-free function of `(arena_id, ordered_action_log)`, NOT of wall-clock timing.** This is the GGPO criterion stated plainly: "for any given game state and inputs, advancing the game state by exactly 1 frame must result in identical game states for all players" ([GGPO Developer Guide](https://github.com/pond3r/ggpo/blob/master/doc/DeveloperGuide.md)). The live loop uses wall-time `dt` (non-reproducible), so we make timing observable, not authoritative:

- Every action is logged with **both** `server_recv_monotonic_ts` **and** the engine's `sim_T` at apply time.
- Every bar crossing logs the integer `T` and the realized fractional `T` at crossing.
- `verify_replay` **re-integrates from the logged sim-time / fixed step**, applying actions in a single canonical order (see R2). It must reproduce the same final equity, positions, resources, and the same per-checkpoint `state_hash`.

This neutralizes the #1 desync source (wall-time jitter) while keeping the live experience real-time. The arena is fixed and pre-normalized (no external I/O mid-match), so the only inputs are the actions.

### R2. Canonical apply-ordering (the single source of determinism truth)

**Resolution — fix one total order and never deviate; `verify_replay` replays in exactly this order.**

1. Actions are ordered by `(sim_T_bucket, server_recv_monotonic_ts, player_id, action_seq)`. The tiebreak chain guarantees a **total order** even for simultaneous actions (player_id then a per-player monotonic `action_seq` break ties). This mirrors CS2-style "timestamp every action, resolve in chronological order" but at our coarse daily-bar granularity.
2. Within a single sim step / bar crossing the fixed sub-order is: **resolve TB → advance `T` → for each newly-crossed integer bar ascending: reveal → trigger resting orders (sorted by `(instr_id, order_id)`) → apply market/sabotage effects → mark P&L → grant realized-P&L IP (+10%) → accrue passive IP (+0.5/s) & TB recharge/consume**. (Same ordering as task-005 R6; documented in both so neither file is ambiguous.)
3. **No reliance on dict/set iteration order** anywhere that feeds state or hashes — always sort by an explicit key. Insertion-order bugs are a classic desync/hash-instability source.

### R3. Decimal everywhere + stable hashing (no float, no `hash()`)

**Resolution — all money/clock/resource math uses `decimal.Decimal` with a fixed module-level context; all hashing uses `hashlib.sha256` over canonically-serialized, quantized data. Never use Python's builtin `hash()` for state.**

Two independent 2026-confirmed pitfalls:
- **Float non-determinism:** floats accumulate platform/order-dependent rounding → desync. Use `Decimal`, set a fixed `getcontext().prec`, and `quantize()` equity/IP/TB to a fixed scale (e.g. `0.01`) before comparing/hashing. Hash a `Decimal` via its canonical string with a domain-defined scale, never its float value ([stable-hashing contract](https://github.com/d-codingGmbH/dvault.development/blob/main/docs/plans/stable-hashing-contract.md)).
- **`hash()` randomization:** Python's builtin `hash()` for `str`/`bytes` is randomized per process via `PYTHONHASHSEED`, so it is useless for cross-run/cross-machine state identity. Use `hashlib` over a deterministic serialization with **sorted keys** ([death-and-gravity: stable hashing](https://death.andgravity.com/stable-hashing), [SO: deterministic hashing](https://stackoverflow.com/questions/27954892/deterministic-hashing-in-python-3), [Python hashlib docs](https://docs.python.org/3/library/hashlib.html)).

```python
from decimal import Decimal, getcontext
import hashlib, json

getcontext().prec = 28          # fixed, ample for 2-4 dp money math
EQ_SCALE = Decimal("0.01")      # equity/IP quantization
TB_SCALE = Decimal("0.01")
T_SCALE  = Decimal("0.000001")  # fractional sim-day

def q(x: Decimal, scale: Decimal) -> str:
    return str(x.quantize(scale))                  # canonical, scale-pinned

def compute_state_hash(engine) -> str:
    # Sort EVERYTHING; only quantized strings, no floats, no platform hash()
    state = {
        "T":  q(engine.T, T_SCALE),
        "R":  q(engine.R, Decimal("0.01")),
        "players": [
            {
                "id": pid,
                "equity": q(p.equity, EQ_SCALE),
                "tb": q(p.tb, TB_SCALE),
                "ip": q(p.ip, EQ_SCALE),
                "positions": sorted(
                    [[k, q(v.size, EQ_SCALE), v.dir, q(v.avg, EQ_SCALE)]
                     for k, v in p.positions.items()]),
                "orders": sorted(
                    [[o.id, o.type, o.instr, q(o.px, EQ_SCALE)] for o in p.orders]),
            }
            for pid, p in sorted(engine.players.items())
        ],
    }
    blob = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()
```

**Arena content hash** (proves both players & the auditor used identical normalized data):

```python
def normalize_and_hash(arena_raw: dict) -> tuple[dict, str]:
    normalized = {}
    for instr, prices in sorted(arena_raw.items()):
        p = [Decimal("100.00")]                      # P[0] = 100.00 (spec §10)
        for ret in compute_returns(prices):          # Decimal returns
            p.append((p[-1] * (Decimal(1) + ret)).quantize(Decimal("0.000001")))
        normalized[instr] = [str(x) for x in p]
    blob = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return normalized, hashlib.sha256(blob).hexdigest()
```

The `arena_hash` is sent in the match-start/snapshot payload (task-005 R5) but the **real symbols/dates are never sent during play** — generic labels only (spec §10). External "I know SPX did X on this date" knowledge is neutralized by normalization-to-100 + private server-side arena + (optional) mystery start offset.

### R4. SyncTest harness — multi-engine identical-input checksum match

**Resolution — port GGPO's SyncTest concept to Python: run N independent engines on the same `(arena, action log)`, assert identical `state_hash` at every periodic checkpoint and at the end.** GGPO's SyncTest runs each frame twice (live + rollback re-sim) and aborts if save-state checksums differ; "by running synctest continuously you identify desync bugs immediately after they're introduced" ([GGPO Developer Guide](https://github.com/pond3r/ggpo/blob/master/doc/DeveloperGuide.md), [ggponet.h synctest](https://github.com/pond3r/ggpo/blob/master/src/include/ggponet.h)). Our adaptation (we have no per-frame rollback, but we have re-sim from log):

```python
# tests/test_determinism.py
def test_synctest_n_engines_identical(arena_id, action_log, n=4):
    arena, arena_hash = normalize_and_hash(load_arena_raw(arena_id))
    checkpoints = [[] for _ in range(n)]
    for i in range(n):
        eng = SimulationEngine(arena, config)
        for act in canonical_order(action_log):       # R2 total order
            eng.apply_action(act)
            eng.advance_to(act.sim_T)                  # fixed-step integrate, not wall time
            if eng.crossed_checkpoint():               # e.g. every integer T, or every K bars
                checkpoints[i].append(eng.compute_state_hash())
        checkpoints[i].append(eng.compute_state_hash())   # final
    assert all(checkpoints[0] == c for c in checkpoints[1:])   # bit-identical at every checkpoint

def test_single_engine_replay_stable(arena_id, action_log):
    # Same input twice in the SAME process and across a fresh process must match.
    a = verify_replay(arena_id, action_log)["state_hash"]
    b = verify_replay(arena_id, action_log)["state_hash"]
    assert a == b
```

`verify_replay` is the post-match audit hook (already sketched in design notes / above):

```python
def verify_replay(arena_id: str, action_log: list[Action]) -> dict:
    arena, arena_hash = normalize_and_hash(load_arena_raw(arena_id))
    eng = SimulationEngine(arena, config)
    for act in canonical_order(action_log):
        eng.apply_action(act)
        eng.advance_to(act.sim_T)
    eng.advance_to_match_end()
    return {
        "arena_hash": arena_hash,
        "final_equity": {pid: q(p.equity, EQ_SCALE) for pid, p in eng.players.items()},
        "state_hash": eng.compute_state_hash(),
        "checkpoint_hashes": eng.checkpoint_hashes,
    }
# On match end: compare verify_replay()['final_equity'] to the live-reported score; mismatch => flag.
```

### R5. Lag-injection testing for TB contention (Pause/FF races, reordering, drops)

**Resolution — a network-fault simulator wraps the action stream; the invariant is that final state + checkpoint hashes are INVARIANT to delivery jitter, given the same logical (sim_T-bucketed) ordering, and that spec contention rules hold regardless of arrival order.** This directly answers the roadmap Tier-1 OQ "testing strategy for lag simulation on clock contention."

Two distinct properties to test:
1. **Determinism under re-ordering within a bucket:** shuffle the wall-clock arrival order of actions that fall in the same `sim_T` bucket; after canonical re-sort (R2) the `state_hash` must be identical. (Confirms the total order, not arrival order, decides state.)
2. **Spec-correct contention under races:** craft adversarial timelines and assert the exact `R` and TB outcomes from `game-mechanics-spec.md §2`:
   - P1 Pause + P2 FFx5 simultaneously ⇒ `R = 0` (Pause overrides); P1 recharges +4/s, P2 pays nothing while `R=0` is forced (P2's FF is overridden — document whether an overridden FF still consumes; **MVP decision: an FF that does not set `R` because Pause wins is treated as not-active for that interval, so it does not consume** — record this and test it).
   - P1 FFx3 + P2 FFx5 ⇒ `R = 5` (max); **both** pay their own rate (5.0/s and 12.0/s). 
   - P1 FFx2 starts, P2 FFx2 starts 0.3 s later ⇒ `R = 2` throughout; both consume only while individually held.
   - FF holder's TB hits 0 ⇒ force-release, `R` recomputes to next-highest active (or 1.0).

```python
# tests/test_lag_contention.py
class LagInjector:
    """Reorders/delays/drops actions, then asserts canonical re-sim is invariant."""
    def __init__(self, delay_fn, drop_p=0.0, reorder=True, rng_seed=12345):
        ...  # seeded RNG ONLY in the test harness, never in the engine

def test_contention_invariant_to_arrival_jitter(arena_id, scripted_actions):
    base = verify_replay(arena_id, scripted_actions)["state_hash"]
    for seed in range(20):
        jittered = LagInjector(delay_fn=rand_delay, reorder=True, rng_seed=seed) \
                       .perturb_arrival_only(scripted_actions)   # same sim_T buckets
        assert verify_replay(arena_id, jittered)["state_hash"] == base

def test_pause_overrides_ff():
    eng = fresh_engine()
    eng.apply(Action(p="P1", type="tb", payload={"mode":"pause","start":True},  sim_T=10.0))
    eng.apply(Action(p="P2", type="tb", payload={"mode":"ff","level":5,"start":True}, sim_T=10.0))
    eng.advance_step(dt=Decimal("1.0"))
    assert eng.R == Decimal("0.0")
    assert eng.players["P1"].tb_delta_last == Decimal("4.0")    # pause bonus recharge
```

### R6. Property-based fuzzing (Hypothesis) for "same inputs → same outputs"

**Resolution — use Hypothesis to generate random-but-valid action streams and assert (a) no exceptions, (b) re-sim reproducibility, (c) invariants.** Hypothesis is deterministic-by-design for CI: it records the seed and **shrinks** any failing input to a minimal counterexample, so a desync surfaces as the smallest reproducing action sequence ([Hypothesis is the standard property-based testing tool for this]). Keep all randomness in the *test*, never in the engine (the engine has no RNG; if news/event randomization is ever added it must be seeded from arena_id per arch §6).

```python
from hypothesis import given, strategies as st, settings

valid_action = st.one_of(
    st.fixed_dictionaries({"type": st.just("tb"),
        "payload": st.fixed_dictionaries({"mode": st.sampled_from(["pause","ff"]),
                                          "level": st.sampled_from([2,3,5]),
                                          "start": st.booleans()})}),
    st.fixed_dictionaries({"type": st.just("order"),
        "payload": st.fixed_dictionaries({"instr": st.integers(0,4),
                                          "side": st.sampled_from(["long","short"]),
                                          "otype": st.sampled_from(["market","limit","stop"]),
                                          "size": st.integers(1,50)})}),
    st.fixed_dictionaries({"type": st.just("ip_spend"),
        "payload": st.sampled_from([{"ability":"delete_sl"},{"ability":"widen"},{"feed":"analytics"}])}),
)

@settings(max_examples=200, deadline=None)
@given(actions=st.lists(valid_action, max_size=300))
def test_fuzz_resim_reproducible(actions):
    log = stamp_with_sim_times(actions)            # assign monotonic sim_T buckets
    h1 = verify_replay(ARENA, log)["state_hash"]
    h2 = verify_replay(ARENA, log)["state_hash"]
    assert h1 == h2                                 # reproducible
    # invariants: TB in [0,100], IP >= 0, equity finite Decimal, R in {0,1,2,3,5}
```

### R7. Periodic in-match checksums (tamper-evidence + early desync alarm)

**Resolution — broadcast a short `state_cs` (truncated `compute_state_hash`) every ~1 s alongside the `clock` delta, and log it.** This mirrors lockstep/GGRS interval-checksum desync detection. For MVP single-process server-authoritative there is no second simulator to disagree, so its value is: (a) **audit trail** — the logged checkpoint hashes let `verify_replay` assert agreement at every checkpoint, not just the end; (b) **future P2P/spectator** re-sim can compare; (c) cheap regression signal in CI. Include arena_hash + ruleset/version in the first checksum so a code change that alters outcomes is detectable (version your hashes).

### Open questions now resolved (task-001 summary)

| Open Q (roadmap/arch) | Resolution |
|---|---|
| How to prove determinism across runs/players | Canonical pure-function contract (R1) + multi-engine SyncTest asserting bit-identical checkpoint+final hashes (R4) |
| SyncTest harness design | N engines on same (arena, sorted log); GGPO-adapted; `tests/test_determinism.py` (R4) |
| Lag-injection for TB contention | Arrival-jitter invariance test + adversarial Pause/FF race assertions vs spec §2 (R5) |
| Decimal + stable hashing | Fixed Decimal context + quantize; `hashlib.sha256` over sorted-key JSON; never builtin `hash()` (R3) |
| `verify_replay(arena_id, sorted_log)` audit flow | Re-sim from logged sim-time, compare final equity + state_hash, auto-flag mismatch (R4) |
| Property-based determinism testing | Hypothesis fuzz: no-exceptions + re-sim reproducibility + invariants; engine stays RNG-free (R6) |
| Proving identical normalized data | `arena_hash` over sorted, Decimal-quantized normalized series; sent as hash only, generic labels (R3) |

**Sources (2026 research):** GGPO Developer Guide (SyncTest, determinism criteria) <https://github.com/pond3r/ggpo/blob/master/doc/DeveloperGuide.md>; GGPO synctest API <https://github.com/pond3r/ggpo/blob/master/src/include/ggponet.h>; coherence determinism/rollback pitfalls <https://docs.coherence.io/manual/advanced-topics/competitive-games/determinism-prediction-rollback>; deterministic Python hashing <https://death.andgravity.com/stable-hashing>, <https://stackoverflow.com/questions/27954892/deterministic-hashing-in-python-3>; stable-decimal hashing contract <https://github.com/d-codingGmbH/dvault.development/blob/main/docs/plans/stable-hashing-contract.md>; Python hashlib docs <https://docs.python.org/3/library/hashlib.html>. Cross-references: `anti-cheat-determinism-design-notes.md` (full pattern catalog), `game-mechanics-spec.md §2 & §10`, task-005 R1/R2/R6 (engine apply-ordering + clock model).
