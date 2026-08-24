# The True Curriculum: Agentic + ML/LLM Systems Engineering (2026)

A layered map of what actually matters right now, synthesized from current industry practice: not a wishlist, a dependency graph. Each layer assumes the one below it. Most engineers over-invest in Layer 0/1 and under-invest in Layers 2-4, which is exactly why ~95% of enterprise agents die in prototype.

---

## Layer 0: Foundations (table stakes, not a differentiator anymore)

You need this to not be dangerous, not to be competitive.

- Transformer architecture: attention, tokenization, positional encoding
- Classical distributed systems: caching, load balancing, database scaling, CAP theorem
- Repos: [rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch), [karpathy/nanochat](https://github.com/karpathy/nanochat), [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer)

---

## Layer 1: Model Lifecycle Literacy

Know what's a *model* problem vs. what's an *engineering-around-the-model* problem. This distinction is the single biggest signal of seniority in FDE/applied AI interviews right now.

- **Pretraining**: scaling laws, data curation, parallelism strategies. [RUCAIBox/awesome-llm-pretraining](https://github.com/RUCAIBox/awesome-llm-pretraining)
- **Post-training**: SFT, RLHF/DPO/GRPO, reasoning-model training. [huggingface/trl](https://github.com/huggingface/trl), [mbzuai-oryx/Awesome-LLM-Post-training](https://github.com/mbzuai-oryx/Awesome-LLM-Post-training)
- **Inference**: serving engines, quantization, KV-cache/PagedAttention, hardware-aware deployment. [vllm-project/vllm](https://github.com/vllm-project/vllm), [NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
- Why it matters: if an agent hallucinates, is that a fine-tuning gap, a context gap, or a harness gap? Most teams guess. You should be able to diagnose.

---

## Layer 2: The Agent Engineering Stack (this is the actual curriculum)

The field has moved through four named phases in ~18 months. Each didn't replace the last. It sits on top of it.

### 2.1 Prompt Engineering (2023, legacy: necessary, not sufficient)

Wording a single request well. Still required, no longer the bottleneck.

### 2.2 Context Engineering (2024-2025)

Curating *what* enters the context window, not what you say. RAG, MCP, project rules, memory retrieval, context compaction. This became systematic once MCP and mature RAG pipelines existed.

### 2.3 Harness Engineering (2026, current center of gravity)

**Agent = Model + Harness.** Treats the LLM as a frozen reasoning utility; safety, execution accuracy, orchestration, and memory become the host application's job, not the model's.

- **Inner harness** (frontier labs build this): native tool-calling, safety layers, raw context windows
- **Outer harness** (you build this, the real moat): environment routing, testing frameworks, situational guardrails
- Five production layers: tool orchestration, verification loops, context/memory, guardrails, observability
- Core discipline (Hashimoto's framing): every time an agent fails, you engineer a structural fix so it *cannot* fail that way again, not a prompt patch
- Reference: [ai-boost/awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering), [DenisSergeevitch/agents-best-practices](https://github.com/DenisSergeevitch/agents-best-practices), [rohitg00/ai-engineering-from-scratch](https://github.com/rohitg00/ai-engineering-from-scratch), and the local `agent-harness-engineering.md` (five components, gate-on-irreversibility, four stop conditions, three-layer evaluation)

### 2.4 Loop Engineering (mid-2026)

Designing the loop that prompts the agent, rather than prompting it yourself turn-by-turn.

- Core elements: **trigger** (what starts it), **topology** (single loop vs. nested), **verifier** (what judges "good enough"), **stop rules** (when it quits)
- The critical insight the field converged on: **the verifier is the bottleneck, not the model.** The generator runs cheaply and repeatedly; what limits quality is how rigorously you can judge output.
- Four nested loops in practice (LangChain's framing): agent loop → verification loop → application loop → hill-climbing loop (the loop that improves the harness itself)
- Distinguish recoverable errors (bad syntax, missing import) from hard blockers (missing credentials). This classification *is* the loop design
- Reference: [cobusgreyling/loop-engineering](https://github.com/cobusgreyling/loop-engineering)

### 2.5 Graph Engineering (July 2026, current frontier)

Loops make one agent's behavior programmable. Graphs make the *organization* of many agents programmable.

- **Org graph**: stable, long-lived. Named roles, owned zones, persists across redeploys. Answers "who."
- **Work graph**: ephemeral. Task nodes exist only while work is in flight, edges split/merge/disappear. Answers "what, right now."
- Nodes aren't all agents: deterministic functions, routers, joins, tools, and human checkpoints are first-class nodes too. Separating *logical judgment* (agentic nodes) from *deterministic computation* (code nodes) is the actual engineering discipline here, not just wiring more LLM calls together.
- Typed handoff contracts and hardcoded policy routers prevent the two failure modes graph engineering exists to solve: context saturation and unbounded delegation
- Frameworks: [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph), AutoGen GraphFlow, Google ADK
- Honest caveat: this framing is ~1 month old as of this writing and contested. Treat it as "LangGraph et al. finally got a shared vocabulary," not a settled standard. Most tasks don't need it.

---

## Layer 3: Agent Development Environments (where you actually build this)

The workspace category above the editor. Not the model, not the harness: the tooling that lets you *ship* agent fleets.

- Core shape: task board → spec-approval gate → isolated git worktree per agent → agent runtime → review layer ending in a PR
- Taxonomy to know cold:
  - **Agentic IDEs** (Cursor, Windsurf): editor stays central, you steer
  - **Agent CLIs** (Claude Code, Codex): one agent, one terminal, full delegation
  - **ADEs proper** (Warp Oz, JetBrains Air): you drive N parallel agents from a board
  - **Agent harnesses/offices**: agents coordinate *each other* under an orchestrator with shared memory and guardrails (this is graph engineering, operationalized)

---

## Layer 4: Evaluation, Observability, and Governance (the layer everyone skips, and why 95% of agents die in prototype)

- **Evals**: computational checks (linters and tests, deterministic) vs. LLM-as-judge (inferential). Know when each applies, and that harnessability should be a first-class architecture criterion, not an afterthought
- **Token/cost economics**: system prompt bloat, context compaction discipline, polling vs. event-driven waits. These are token-economics decisions made by default, not by design, in most production harnesses
- **Security**: prompt injection, tool permission models, unbounded delegation, the same failure modes graph engineering's typed handoffs and policy routers exist to close
- **Observability**: correlated graph/run/node identifiers so a failure trace is reconstructable, not just a log line

---

## Layer 5: The MLOps Substrate Underneath All of This

Unglamorous, still load-bearing.

- CI/CD for ML, model lifecycle management, drift/monitoring
- Infra: Docker/K8s/GPU scheduling, distributed training when you actually need it
- Repos: [ai-infra-curriculum/ai-infra-engineer-learning](https://github.com/ai-infra-curriculum/ai-infra-engineer-learning), [amanchadha/coursera-machine-learning-engineering-for-prod-mlops-specialization](https://github.com/amanchadha/coursera-machine-learning-engineering-for-prod-mlops-specialization)

---

## Layer 6: Applied Grounding (the case-study corpus)

Everything above is architecture theory until you can point to how it failed or worked somewhere real.

- Classic ML production case studies (pre-agent era): [Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies](https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies)
- GenAI/LLM/agent production case studies (current era): [themanojdesai/genai-llm-ml-case-studies](https://github.com/themanojdesai/genai-llm-ml-case-studies)
- Agentic design patterns specifically: ~~sarwarbeing-ai/Agentic_Design_Patterns~~, taken down via DMCA (Springer, Feb 2026); use [ai-boost/awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering) as the living substitute

---

## What this means for the playbook

Your current five architectures (coding assistant, support agent, data pipeline, memory system, multi-agent orchestration) are Layer 2-3 content, but they were framed before the harness/loop/graph vocabulary existed. The multi-agent orchestration section in particular is now better described as **graph engineering**. Org graph vs. work graph is a sharper decomposition than "supervisor + specialists." The memory system section maps cleanly onto the harness's context/memory layer. Worth a pass to re-anchor terminology and add the verifier-as-bottleneck framing to every architecture's evaluation checklist, since that's the one idea that cuts across all five.
