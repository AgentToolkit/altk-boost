"""Shared evaluation principles injected into every function-calling metric prompt.

These were previously duplicated across 5 runtime JSON files. Centralizing
them keeps production-quality guardrails consistent and keeps the per-metric
``task_description`` focused on what's unique to that metric.

The block is injected via ``FunctionMetricsPrompt.__init__`` into the system
template placeholder ``{{ common_principles }}``.
"""

# Keep this block concise — every metric prompt pays for it in tokens.
COMMON_PRINCIPLES = """\
### Common Evaluation Principles

Apply these rules across every judgment. They override anything in the
task description that conflicts with them.

1. Evidence hierarchy — when sources disagree, trust them in this order:
   system prompt > tool outputs > user messages > assistant messages.
   Treat values the system prompt fixes (policy, current date/year,
   identity, environment anchors) as ground truth even if an assistant
   turn contradicts them.
2. Trajectory awareness — the call under review may be one step in an
   ongoing trajectory; additional tool calls may follow and will be
   judged separately. Do NOT penalize a call for not, by itself,
   completing the user's full goal.
3. Redundancy — the clearest case is when a prior call used the SAME
   function name AND the SAME arguments AND its result is still valid.
   Two other patterns also count:
   - Information already obtained: a prior tool output contains the
     value the agent is now re-querying, or the agent re-reads a
     record it just wrote in the same turn.
   - Parameter-permutation spinning: the agent calls the SAME function
     again after a prior same-function call returned empty or errored,
     with only reordered arguments, flipped boolean flags to their
     defaults, pagination bumps on an empty result set, or similar
     surface changes — and NO new conversational information has
     arrived since the prior call. Legitimate recovery requires a
     different strategy: a different tool, an argument change grounded
     in new information the agent just received, or a user-intent
     pivot. Shuffling surface params on a dead query is not recovery.
   Beyond these patterns, different arguments or a meaningful change
   in context (time, state, scope) are exploration, not redundancy.
4. Recovery after failure — if earlier tool calls returned empty
   results, errors, or validation failures, subsequent calls that try
   different parameters, alternative tools, or fallback strategies are
   legitimate recovery. Do not fault "should have called X first" when
   X already ran and failed.
5. Read-only exploration passes — a read-only or information-gathering
   call that is plausibly relevant to the user's request should be
   APPROVED even if strictly unnecessary, UNLESS it exposes sensitive
   data the user did not authorize or contradicts an explicit scope.
6. Evidence-based judgment — base every label on explicit evidence.
   When evidence is ambiguous, do NOT fabricate a problem. Plausible
   parameters from visible context are not "hallucinated" merely
   because the value is not repeated verbatim elsewhere.
"""
