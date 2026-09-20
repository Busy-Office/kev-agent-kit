# Practical Use Cases

These are workflows you can try, not claims of deployed customer systems. The
support example below includes an actual local test observation. The other cases
are proposed experiments; the kit has no built-in ticketing, email, or CI connector.

## 1. Customer Support: Draft A Routing Recommendation

**Situation:** A support worker receives a complaint about a duplicate charge.
They want a suggested department, an extracted concern, and a reply draft.

**Prompt:**

> Use Kev to assess this message: “I was charged twice for my shoes. Please refund
> the duplicate charge.” Ask which department should handle it, whether it reports
> a duplicate charge, and how angry the customer sounds. Show the distributions,
> check them against the text, and draft a reply. Do not send the reply or issue a refund.

**Workflow:** The agent submits the message and three typed questions. Kev returns
predictions. The agent checks whether they make sense and drafts a response for
the support worker. The worker decides how to route the case and what to send.

**What actually happened in our local test:** The default `jaredpalmer/kev-0.5b`
checkpoint received the request now saved in
[`examples/support-triage.json`](../examples/support-triage.json). One observed run
returned these results:

| Question | Observed output | Interpretation |
| --- | --- | --- |
| Department | billing 0.00; shipping 0.00; other 1.00; confidence 1.00 | Incorrect: the text directly describes a billing issue |
| Duplicate charge? | yes probability 0.96 | Consistent with the text |
| Tone | calm 0.07; frustrated 0.45; furious 0.48; score 1.41 | A subjective estimate; wording alone does not establish the customer's emotional state |

This is a recorded example, not a benchmark or a guarantee of identical results
after changing models or inputs. A simpler two-option billing/shipping request
in the smoke test returned billing 1.00, but its wording and options also differed;
that does not isolate the cause of the first failure.

**Practical consequence:** Initially use Kev in review mode. Compare recommendations
with human labels before allowing automatic routing. A confidence of 1.00 did not
make the observed answer correct. Coding-agent reasoning remains useful for spotting
this disagreement; it too needs verification for consequential actions.

## 2. Engineering: Triage A Failing CI Job

**Situation:** Several jobs failed after a change. An engineer wants help choosing
where to investigate first.

**Prompt:**

> Read the supplied CI log and diff. Use Kev as a second opinion to classify the
> failure as application code, test expectation, environment, or unknown. Show the
> probabilities. Verify the strongest hypothesis against the log and source before
> recommending a fix. Do not modify files yet.

**Kev's role:** Rank a constrained set of hypotheses using the evidence the agent
provides. **The main agent's role:** Read source, reproduce the failure where possible,
and explain the diagnosis. A later request to fix it can authorize edits and tests.

**Example:** If the log says `DATABASE_URL is missing`, the exact log message is
stronger evidence than a model's guess. Check configuration directly. Kev adds
little value to that case; ambiguous repeated failures are a more useful experiment.

**Limit:** CI diagnosis is outside this checkpoint's demonstrated training domains.
Do not let a high score skip tests, approve a merge, or select a production rollback.

## 3. Product Work: Sort Feedback Before Reading It

**Situation:** A product owner has a set of short feedback messages and wants an
initial grouping into usability, performance, billing, feature request, and unknown.

**Prompt:**

> Use Kev to suggest a topic and sentiment for each supplied feedback message.
> Preserve each original message and its probabilities. Flag disagreements or
> unclear cases for my review, then summarize themes without inventing counts.

**Workflow:** Send one message as state per request, asking topic and sentiment
together. The adapter batches questions about one state, not unrelated documents.
For many messages, an application would need its own iteration, retry, and storage
logic. The current server serializes inference, so more concurrent calls do not
necessarily improve throughput.

**Success criterion:** Compare the proposed groups with a small human-labelled set.
Measure topic errors, uncertain cases, and total time, then decide whether this
step is worth including. This kit does not yet supply a bulk feedback pipeline.

## 4. Code Review: Suggest Areas To Inspect

**Situation:** An agent is reviewing a patch and wants a second opinion about
which concern deserves closer inspection: correctness, performance, compatibility,
or insufficient context.

**Prompt:**

> Inspect this patch and its relevant callers. Ask Kev which review category most
> deserves investigation. Treat the result as a suggestion. Report a finding only
> when you can identify a concrete code path and explain the observable failure.

**Output:** An evidence-backed review, optionally explaining where the agent agrees
or disagrees with Kev. A risk score alone is not a finding. This is an experimental
coding use case; no accuracy improvement has been established for this kit.

## How To Decide Whether To Keep Kev In Your Workflow

1. Collect a small representative set of examples with reviewed expected answers.
2. Keep a separate set for evaluation when changing wording or options.
3. Compare Kev-assisted work with your current agent-only or rule-based workflow.
4. Record wrong high-confidence answers, timeouts, full end-to-end latency, and
   human review effort—not just the service's inference time.
5. Keep it advisory unless your own evaluation supports a specific bounded use.

Starting with roughly 50–100 labelled examples can reveal obvious problems, but
is not enough to establish reliability for rare or high-impact failures. No such
domain-specific evaluation is included in this project's integration tests.
