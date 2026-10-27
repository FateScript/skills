> 本文件是 `who-ate-my-flops` 的内部流程。`<skill root>` 指主 `SKILL.md` 所在目录；文中提到的其他流程均按主入口的映射读取同目录下的 Markdown 文件，无需安装同名 skill。

optimize is a sequence of steps. Work through them one at a time and mark each
one done as you go.

# Step 1: setup

Use the setup-baseline skill. It builds the worktree and the workspace, has
extract-computation-graph write `records/computation_graph.json` and
`records/execution_schedule.json`, then measures the base commit for speed, memory and
correctness, profiles it in full with torch-profile, and records it with
`workspace.py add --verdict base`. `diagnose` begins the same way, which is why
that work lives in one skill and not in this one.

Setup can fail in a way worth handing back, and setup-baseline says so when it
does. Stop there rather than arming a campaign on a baseline that did not hold.

# Step 2: arm the loop

Arm once setup has passed, and from there the campaign runs until `finish` says
it is over.

```bash
python <skill root>/tools/workspace.py arm <ws>
```

That records which session owns the campaign, read from `CODEX_THREAD_ID`
or `CLAUDE_CODE_SESSION_ID`. If neither exists, use `arm --session <unique-id>`
and preserve that ID for this campaign.

Continue the optimization loop in the current turn. Before stopping, run
`python <skill root>/tools/workspace.py finish <ws>`. If it reports outstanding
work, address it and continue. Stop when it passes, the user asks you to stop,
or a blocker requires user input or an unavailable external resource. Report
what is blocked and what is needed to resume. This standalone skill installs
no timer or Stop hook.

`workspace.py finish <ws>` is the loop condition, and it hands back what is
outstanding: the contract settled, the graph and schedule built, a baseline
and any candidates recorded, every rejection carrying its reason,
each measurement filled in or explained, the report closed with a
`status: closed` line, and `records/candidates.jsonl` in step with `benchmark.csv`.
Once it passes it takes the campaign off the registry itself.

The user settled everything before the loop began. If you find yourself
about to ask them something, re-read `<ws>/contract.md`, take the reading it
supports, say in one line which one you took, and continue. If the node was
taken or the job stopped running, explain the blocker and attempt recovery.
If recovery requires external help, report what is needed rather than retrying
indefinitely.


# Step 3: optimization loop

Profile the current code, analyze and find what can be improved, and keep the profile and
edit loop turning until nothing worth doing is left.

- Every change has to pass the recorder's comparison against the baseline.
- Use the torch-profile skill to see what the GPU is doing at runtime. It also
  analyses the profile data and reads it against the code and the computation
  graph built earlier, so both the surface problems and the underlying ones come
  out.
- Let those findings decide whether you keep or drop the change behind a
  commit. You write one round of optimization and create the commit.
- Keep each optimization short so that agent can understand better where improvements come from. 
- When you get something wrong, write it to `records/mistakes.md` in the same turn: what
  you did, what caught it, and what in this plugin should have caught it sooner.
- Record every commit's result clearly. workspace.py has the format, and staying
  consistent with it is what matters. A later reader should be able to
  reconstruct what changed, what was measured, and why a candidate was promoted.
- Fill all four measurements for every run, including rejected candidates.
  If one is unavailable, explain why: `--peak-cpu-gb "N/A: collection failed"`.
- Log the commits with their results and findings, in order, in
  `records/candidates.jsonl`. The plainer performance numbers go in `benchmark.csv`.
- During the loop you may adjust the benchmark script, but only when the
  measurement itself has broken down, never to make a candidate look better:
  - profiling time or trace file size has got out of hand
  - a change moved the warmup, so the window no longer sits on steady steps. The
    first `torch.compile` can move it by minutes
  - the steady step got fast enough that 5 to 10 of them is mostly noise
  - the job got fast enough to run whole, so there is nothing left to truncate
  - something excluded at init has been promoted into the top few percent by
    everything you sped up around it
- An adjustment invalidates every number taken before it. Measure the baseline
  again by running setup-baseline's step 4 under the new script, measure the
  current head the same way, record the change as its own entry in
  `records/candidates.jsonl`, and say so in the report.
- When either file drifts too far from the code, rebuild it, and record which
  commit the new one describes. 

## Tradeoffs

Stay within the scope of changes agreed in contract.md.

Most findings have more than one fix. Speed is the goal, but do not give these
up unless you have to.

- Architecture: go through the acceleration path the codebase already has, its
  fused kernel, its fast attention backend, its compile flag, instead of adding
  one beside it.
- Breadth: prefer the fix that touches least, a dependency or a setting before
  a code change, and keep a code change small enough to read in one sitting.
- Memory: speed bought with memory needs the headroom to be there, so read view
  5 and what the contract allows before spending it.
- Precision: the recorder decides, at the tolerance derived at setup, and a fix
  that needs it widened is rejected rather than re-measured.

No special case keyed on this model, this shape, this hardware or this
benchmark. A change that only pays off at the benchmark's shape is rejected for
that reason.

## Promotion rule

Promote a candidate only when it satisfies the contract and there is evidence
that it improved the target metric, or at least held it. Between two candidates
with the same gain the less invasive one wins, and a code change that a
dependency or a setting could have replaced is rejected with that as the
reason. When a candidate is rejected, write down why instead of quietly
dropping it.

# Step 4: closing

1. Write a brief `latest-report.md` with a standalone `status: closed` line.
   If no candidate was worth trying, explain why from the baseline findings.
2. Run `python <skill root>/tools/workspace.py finish <ws>` and resolve its findings.
3. Run the clean-up procedure to prepare the delivery branch and final handover.
