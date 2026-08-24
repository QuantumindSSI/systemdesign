# Agent Harness Engineering: The Five Components and the Evaluation Layer

Core reference distilled from *AI Engineering from Scratch* ([rohitg00/ai-engineering-from-scratch](https://github.com/rohitg00/ai-engineering-from-scratch)) and its DevVoice worked example (a five-agent pipeline: GitHub README → reviewed X thread, LinkedIn post, dev.to article). Companion to `curriculum.md` Layers 2.3-2.4 and Layer 4.

**Thesis:** put a frontier model into a badly designed agent system and you get a more articulate failure. Nearly all of the engineering sits outside the model, in the harness. Code samples are illustrative pseudocode. Adapt to your framework.

---

## Part 1. Agent Workloads Are Not Web Workloads

A web request is 50-200ms, CPU-bound in bursts, deterministic, and costs ~nothing per unit. An agent job is none of those things. Four architectural consequences:

1. **Duration**: you cannot answer synchronously; load balancers have idle timeouts. Holding a connection open for two minutes per job is wasteful.
2. **I/O-bound**: workers spend 70-80% of their time waiting on the model API. A 2-core container runs dozens of concurrent jobs; sizing for core count wastes what you pay for.
3. **Non-determinism**: same input, different output. Retries are not free; CI cannot assert on output, so tests must target the harness, not the model.
4. **Marginal cost**: a bug is a bill. A runaway agent loop burns roughly a dollar a minute, silently, until someone notices.

Design for this shape from the first commit and deployment is configuration. Design for the web shape and deployment is a rewrite.

## Part 2. The Harness: What You Build That Isn't the Model

### Component 1: Tools

Tools are the agent's only way to affect the world. Designed well, they cut context by ~60%; designed badly, they waste tokens on confusion.

```python
@tool
def search_code(query: str, repository: str, max_results: int = 10) -> list[CodeMatch]:
    """Search for code patterns across a repository.

    Args:
        query: The code pattern or keyword to search for
        repository: GitHub org/repo identifier
        max_results: Limit results (default 10, max 100)

    Returns:
        List of matching code locations with context
    """
```

Three requirements:
- **Typed inputs and outputs**: the model sees the schema; ambiguity costs tokens and errors.
- **Small surface area**: one tool per discrete action; five focused tools beat one with five optional parameters.
- **Deterministic and fast**: a 30-second tool is a context killer; make expensive operations async with a status-poll tool or a task queue.

Management: keep tools in a registry, version tools separately from agents (`search_v2` alongside `search_v1`), log every call with arguments and latency, and put a timeout on every tool. A hung tool stalls the agent.

### Component 2: Prompts

Prompts are not prose. They are state machines. Order: **(1)** system prompt → **(2)** static examples → **(3)** tool specification → **(4)** dynamic context (history, per-request data, job state) → **(5)** user turn.

**The cardinal rule: static content precedes dynamic content.** Every dynamic value that leaks upward nukes the prompt cache and quietly doubles token cost.

Version prompts, and version response-cache keys with them: a bad prompt gets cached and served for hours after you fix it; with versioning, rollback is one env-var change.

### Component 3: Memory

Two kinds, not interchangeable:
- **Working memory** (short-term, in-context): current turn, last-N messages, retrieved context. Budget = whatever fits in context.
- **Persistent memory** (long-term, storage-backed): preferences, learned facts, evaluation results. Stored indefinitely.

The mistake is treating working memory like persistent memory: re-sending "remember X" every turn burns tokens. Pattern: **seed working memory at job start** (user facts, last-5 interactions, retrieved docs) → work from it → **write back learned facts at job end**. Avoid overflow by truncating intelligently (drop oldest, keep most relevant), summarizing long histories into persistent memory, and chunking documents at section boundaries, not token limits.

### Component 4: Orchestration

Parallel agents sound efficient; they mostly create a coordination problem (polling + merging). **Sequential subagents win**: clear data flow (B explicitly depends on A), early exit on invalid intermediate output, simpler state (threaded in order), easier debugging (one input, one output per agent).

```python
class Orchestrator:
    def run(self, job: Job) -> Result:
        extracted = self.extract_agent.run(job.content, job.schema)
        validated = self.validator_agent.run(extracted, job.rules)
        formatted = self.formatter_agent.run(validated, job.format)
        return Result(data=formatted, trace=self.trace)
```

Use parallel only when outputs genuinely never interact, and even then consider sequential with fallback.

### Component 5: Human in the Loop

An agent that can only read is safe and not very interesting; the moment it can send, publish, or spend, some actions stop being undoable. **Gate on irreversibility, not importance**. The test is mechanical: *can another tool call undo this?* Reading/retrieving/drafting pass; publishing/sending/deleting/spending do not.

Over-gating is the failure that looks like caution: a gate that fires on everything trains the reviewer to click approve without reading. You pay the latency and keep none of the safety. Gates keep their meaning by being rare. The gate is a **state the run rests in**, not a blocking call.

### Loop Engineering vs Graph Engineering

- **Loop engineering** covers one agentic node: one agent, one goal, a verifier, a stop condition.
- **Graph engineering** covers the topology around those loops: which nodes exist, which transitions are legal, what state crosses each edge.

Not rivals: a graph is what you build when one loop stops being enough, and every node in it is still a loop. The distinction decides what a gate can promise: in a loop the gate is a tool the model chooses to call (holds only as well as the model's judgment); in a graph it is a node on an edge, and the irreversible step has **no path around it**. Start with a loop; move a decision into the graph when its failure should be impossible rather than unlikely, usually the irreversible ones, usually first.

### Stop Conditions

A model deciding it is finished is the least reliable stop condition you have. Add three more: a **step budget**, a **wall-clock budget**, a **token budget**. The model owns one exit; you own the other three. A loop that stops making progress does not error: every call succeeds, and it bills ~a dollar a minute until someone notices.

## Part 3. Evaluation and Metrics

Design evaluation before you design agents. Three layers:

1. **Harness correctness** (deterministic, CI-testable): orchestration flow, tool schemas, state transitions, result assembly.
2. **Agent output quality** (non-deterministic, sampling-based): spec match, factual accuracy, sound reasoning, correct format.
3. **End-to-end regression** (automated, periodic): fixed test set weekly, judged against baseline, regressions flagged before production.

### LLM as a Judge

A specialized agent with one job: score output against a rubric, returning structured results (value 0-10, reasoning, failures, confidence, suggested fix). Use it to score a daily sample (100-200 jobs), alert when P50 drops below baseline − 1σ, compare variants A/B on the same test cases, and grow the test set from every failure pattern found.

**Test the judge itself**: it must separate known-good from known-bad outputs; two judge instances disagreeing on edge cases means the rubric is ambiguous; judge scores should correlate with human scores.

### Continuous Evaluation

Weekly eval run over a sampled set with a regression threshold (alert if mean drops > 0.5 below baseline); A/B testing via judge with a ship/revert margin (e.g., ship only if new variant clears old by +0.3).

## The Scorecard

Not every system builds all of these; every system has all of them **decided**. The only question is whether you decided or defaulted:

1. **Tools**: few, one action each, tightly typed, with a timeout and a log line
2. **Prompts**: static before dynamic, versioned, cache key versioned with them
3. **Memory**: working and persistent kept apart, seeded once rather than re-sent
4. **Orchestration**: sequential subagents over parallel; state flows one way
5. **Human in the loop**: gate on irreversibility, not importance; rare enough to stay meaningful
6. **Loop vs graph**: start with one loop; move decisions into the graph when failure should be impossible rather than unlikely
7. **Stop conditions**: four exits, only one of which the model owns
8. **Evaluation**: harness tested on every commit; output sampled and judged out of band

Notice how little of that is about the model. Swap the model underneath and all eight survive unchanged, which is the argument for treating them as the actual engineering rather than the plumbing around it.

## Further Reading

- [rohitg00/ai-engineering-from-scratch](https://github.com/rohitg00/ai-engineering-from-scratch). The source curriculum (installed locally as `.agents/skills/`: learn, course-guide, check-understanding, find-your-level, start-learning, claude-certification)
- [ai-boost/awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering). Curated taxonomy across all of these areas
- [cobusgreyling/loop-engineering](https://github.com/cobusgreyling/loop-engineering). Loop patterns, verifier and stop-rule design
- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph). The framework side of the graph argument
- `curriculum.md` Layers 2.3-2.5: harness → loop → graph phase framing; Layer 4: evals and governance
