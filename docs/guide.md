# AgentOS in plain words — a guide for a human

## What this even is

Imagine a small assembly line where code is written not by you and not by me,
but by robots, while you are the customer and the quality controller.

Three participants on the line:

1. **The board** — a pile of sticky notes with tasks. You write a note "do
   such-and-such", put it on the board — and go mind your own business.
2. **The worker robot** — picks up the note, writes code from it. That's OpenCode.
3. **The checker** — a script that a machine can't fool. It checks the result:
   the file exists, isn't empty, compiles, has no forgotten passwords or keys
   in it. If it says "good" — it's good; if it says "defect" — it's a defect.

The main rule: **nobody says "done" on their word.** "Done" only counts when
the checker agrees. The robot can lie, the script can't.

## How to use it: three steps

### Step 1. Leave an order

Write a task note — the more precisely you describe it, the fewer reworks:

```bash
hermes kanban create "Add /health to FastAPI" \
  --body "endpoint in src/api/health.py, responds 200 and {status:ok}, test in tests/" \
  --assignee opencode \
  --workspace dir:~/Projects/my-app
```

The note's body IS the assignment: what to do, where it lives, how we know
it's done.

### Step 2. Start the line

```bash
hermes kanban dispatch --max 3
```

Or do nothing at all: with the auto-dispatcher enabled (the gateway service),
ready notes get picked up by themselves every minute.

What happens next — without you: the robot read the note → wrote the code →
the checker checked it → if it's a defect, the robot automatically gets one
attempt to fix it (with the error text) → if that fails, the note is marked
"stuck".

### Step 3. Come back and look

```bash
hermes kanban list              # what's done, what's stuck
hermes kanban show <id>         # full history of one task
```

- **done** — finished, but the machine checked "not empty and not broken",
  not "good". Open it, look with your eyes, commit. The final review is
  always yours.
- **blocked** — stuck. Read the reason (the checker writes what's wrong),
  fix the note (`hermes kanban edit <id>`) and rerun.

## Magic words in the note

You can put switch-lines into the note body. They work like checkboxes:
the line is there — the feature is on; no line — everything as before.

| Line in the note | What it does |
|---|---|
| `model: <id>` | write the code with a different model (list: `opencode models`) |
| `timeout: 300` | task might hang? after 300 seconds the robot is killed and the task goes back for a rework. `timeout: default` = 10 minutes |
| `gate: 120` | dangerous task: after checking, the code is NOT handed over but waits for your "APPROVED" for 2 minutes. Not confirmed — the task is blocked. `gate: default` = 2 minutes |

A bit more about `gate`, because it's about trust. Mark tasks that touch
something important this way (deploys, deletions, other people's data). The
ticket stops at the final point and waits for you. Confirm — one command:

```bash
hermes kanban comment <id> APPROVED
```

Within a couple of seconds the worker sees the confirmation and hands the task over.

## If something went wrong

- **The task hangs and doesn't move** — `hermes kanban reclaim <id>` takes it
  back into the queue.
- **Want to check a file by hand** — `python3 verify.py <file>` will say
  good/defect.
- **Want an overall board report** — `./report.sh default` (or
  `./report.sh --machine default` if another script will read the report — it
  outputs ERR_/OK_ lines that are convenient to grep).
- **A secret accidentally got into a commit** — it won't: the pre-commit hook
  catches that.

## What not to do

- Don't write code for the robot yourself — the whole point is that you're
  only the customer and reviewer.
- Don't create a board "for the future". Board = a living project.
- Don't run more tasks than you're ready to review in an evening: a pile of
  done without your review is not readiness, it's a warehouse.

## In one sentence

You write notes → robots write code → a script decides whether the result is
good → you only look at the finished and the important. That's all.
