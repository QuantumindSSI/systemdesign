"""Content calendar generator: 2 posts/day, Sun-Sat, 100 weeks (1,400 posts).

Deterministic - no randomness. Concepts are drawn from a structured bank built
from curriculum.md and files.md. The 100 weeks form 5 editorial passes over 10
content pillars (2 weeks per pillar per pass); a concept may recur across
passes but always with a different editorial angle and format, and every
working title is asserted globally unique.

Outputs (written next to this script):
  content_calendar.csv          - 1,400 rows, one complete brief per post
  content_calendar_overview.md  - system documentation + 100-week index

Run: python3 generate_calendar.py
"""
from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta

START_DATE = date(2026, 8, 23)  # first Sunday after 2026-08-20
WEEK0_START = date(2026, 8, 20)  # launch block: Thu/Fri/Sat before week 1
WEEK0_POSTS = 6
WEEKS = 100
POSTS_PER_DAY = 2
AM_TIME = "09:00"
PM_TIME = "17:00"

# --------------------------------------------------------------------------
# Content pillars: (key, name, source references rotated across posts)
# --------------------------------------------------------------------------
PILLARS = [
    ("P1", "System Design Fundamentals", [
        "github.com/donnemartin/system-design-primer",
        "github.com/karanpratapsingh/system-design",
        "github.com/ByteByteGoHq/system-design-101",
        "github.com/binhnguyennus/awesome-scalability",
        "github.com/ashishps1/awesome-system-design-resources",
    ]),
    ("P2", "LLM Internals & Pretraining", [
        "github.com/rasbt/LLMs-from-scratch",
        "github.com/karpathy/nanochat",
        "github.com/RUCAIBox/awesome-llm-pretraining",
        "github.com/FareedKhan-dev/train-llm-from-scratch",
    ]),
    ("P3", "Post-training & Alignment", [
        "github.com/huggingface/trl",
        "github.com/mbzuai-oryx/Awesome-LLM-Post-training",
        "github.com/OpenRLHF/OpenRLHF",
        "github.com/hiyouga/LlamaFactory",
    ]),
    ("P4", "Inference & Edge Deployment", [
        "github.com/vllm-project/vllm",
        "github.com/NVIDIA/TensorRT-LLM",
        "github.com/ggml-org/llama.cpp",
        "github.com/xlite-dev/Awesome-LLM-Inference",
    ]),
    ("P5", "Harness Engineering", [
        "github.com/ai-boost/awesome-harness-engineering",
        "github.com/DenisSergeevitch/agents-best-practices",
        "curriculum.md Layer 2.3",
        "github.com/rohitg00/ai-engineering-from-scratch",
        "agent-harness-engineering.md",
    ]),
    ("P6", "Loop & Graph Engineering", [
        "github.com/cobusgreyling/loop-engineering",
        "github.com/langchain-ai/langgraph",
        "curriculum.md Layers 2.4-2.5",
    ]),
    ("P7", "Evals, Observability & Governance", [
        "curriculum.md Layer 4",
        "github.com/ai-boost/awesome-harness-engineering",
        "github.com/DenisSergeevitch/agents-best-practices",
    ]),
    ("P8", "MLOps & Infrastructure", [
        "github.com/ai-infra-curriculum/ai-infra-engineer-learning",
        "github.com/amanchadha/coursera-machine-learning-engineering-for-prod-mlops-specialization",
        "curriculum.md Layer 5",
    ]),
    ("P9", "Production Case Studies", [
        "github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
        "github.com/themanojdesai/genai-llm-ml-case-studies",
        "github.com/binhnguyennus/awesome-scalability",
        "curriculum.md Layer 6",
    ]),
    ("P10", "Career, FDE & Interviews", [
        "github.com/alexeygrigorev/ai-engineering-field-guide",
        "github.com/chiphuyen/machine-learning-systems-design",
        "github.com/checkcheckzz/system-design-interview",
        "curriculum.md Layer 1",
    ]),
]

# --------------------------------------------------------------------------
# Concept bank per pillar (natural noun phrases; each week consumes six)
# --------------------------------------------------------------------------
CONCEPTS: dict[str, list[str]] = {
    "P1": [
        "the CAP theorem", "PACELC tradeoffs", "consistent hashing",
        "load balancing algorithms", "L4 vs L7 load balancing",
        "reverse proxies", "CDN architecture", "DNS resolution paths",
        "cache-aside vs write-through caching", "cache eviction policies",
        "cache stampede protection", "database indexing", "B-trees vs LSM trees",
        "SQL vs NoSQL selection", "database sharding strategies",
        "leader-follower replication", "leaderless replication and quorums",
        "Raft consensus", "two-phase commit vs sagas", "event sourcing",
        "CQRS", "message queue semantics", "Kafka partitioning",
        "exactly-once delivery", "idempotency keys", "rate limiting algorithms",
        "circuit breakers", "bulkhead isolation", "backpressure",
        "service discovery", "API gateway design", "gRPC vs REST",
        "GraphQL tradeoffs", "WebSockets vs server-sent events",
        "bloom filters", "HyperLogLog cardinality estimation", "geohashing",
        "distributed unique ID generation", "clock skew and vector clocks",
        "gossip protocols", "back-of-envelope capacity estimation",
    ],
    "P2": [
        "self-attention mechanics", "multi-head attention", "BPE tokenization",
        "embedding layers", "rotary positional encodings",
        "pre-norm vs post-norm layer normalization", "residual streams",
        "feed-forward blocks", "grouped-query attention",
        "multi-head latent attention", "sliding-window attention",
        "DeepSeek sparse attention", "mixture-of-experts routing",
        "Chinchilla scaling laws", "pretraining data curation",
        "dataset deduplication", "tokenizer training", "data mixture weighting",
        "data parallelism", "tensor parallelism", "pipeline parallelism",
        "ZeRO and FSDP sharding", "gradient checkpointing",
        "BF16 and FP8 mixed precision", "optimizer choice for pretraining",
        "learning-rate warmup and cosine decay", "loss spikes and training stability",
        "checkpoint-resume discipline", "perplexity evaluation during pretraining",
        "compute budgeting for training runs", "the nanochat pipeline stages",
        "KV cache formation during training vs inference",
        "curriculum ordering of training data", "vocabulary size tradeoffs",
        "the emergent-abilities debate",
    ],
    "P3": [
        "SFT data quality vs quantity", "chat templates and instruction formats",
        "LoRA mechanics", "QLoRA quantized fine-tuning",
        "full fine-tuning vs PEFT", "reward model training",
        "the RLHF pipeline end to end", "PPO for language models",
        "DPO mechanics", "DPO vs PPO tradeoffs", "GRPO", "ORPO", "KTO",
        "rejection sampling and best-of-n", "RLAIF and constitutional methods",
        "reasoning-model training with long chain-of-thought",
        "distillation from teacher models", "verifiable rewards (RLVR)",
        "reward hacking", "KL penalties and policy drift",
        "catastrophic forgetting in fine-tuning", "the alignment tax",
        "preference data collection", "synthetic training data generation",
        "self-improvement loops", "safety tuning vs helpfulness",
        "post-training eval suites", "OpenRLHF's Ray + vLLM architecture",
        "TRL trainer anatomy", "LlamaFactory workflow design",
    ],
    "P4": [
        "KV cache memory math", "PagedAttention", "continuous batching",
        "prefill vs decode phases", "disaggregated prefill/decode serving",
        "speculative decoding", "draft-model design", "INT8 quantization",
        "INT4 quantization", "FP8 inference", "GPTQ vs AWQ",
        "GGUF quantization levels", "KV cache quantization",
        "FlashAttention kernels", "time-to-first-token vs throughput",
        "p99 latency budgets", "cost per million tokens",
        "vLLM vs TensorRT-LLM vs llama.cpp selection",
        "OpenAI-compatible serving APIs", "grammar-constrained decoding",
        "prompt caching", "batching strategies for agent workloads",
        "on-device backends: Metal, CUDA, NPU", "model selection for edge hardware",
        "context length vs memory tradeoffs", "air-gapped sovereign deployment",
        "multi-tenant model serving", "GPU fleet autoscaling",
        "small-model-first routing cascades", "embedding model serving",
        "streaming token delivery", "tool-call latency budgets",
        "energy constraints at the edge", "hardware-aware model choice",
    ],
    "P5": [
        "the agent = model + harness equation", "inner vs outer harness boundaries",
        "tool orchestration layers", "tool schema design",
        "verification loops inside the harness", "context and memory layers",
        "guardrail layers", "harness observability",
        "structural fixes over prompt patches", "tool permission models",
        "sandboxing and isolation", "environment routing",
        "deterministic wrappers around tools", "bounded retry policies",
        "error taxonomies: recoverable vs hard blockers",
        "harnessability as an architecture criterion",
        "system prompts as configuration", "context compaction",
        "memory retrieval strategies", "MCP fundamentals",
        "MCP server design", "project rules files", "agent skills packaging",
        "regression suites for agent behavior", "prompt injection defenses",
        "cost guards and budget enforcement",         "event-driven vs polling waits",
        "human-in-the-loop checkpoints", "agent CLI vs agentic IDE harnesses",
        "testing harnesses for agents",
        "agent workloads vs web workloads", "I/O-bound concurrency sizing",
        "runaway loop economics: a bug is a bill",
        "tool contracts: typed inputs and outputs",
        "tool registries and independent tool versioning",
        "tool timeouts and call logging", "prompt structure as a state machine",
        "static-before-dynamic prompt ordering",
        "prompt versioning and cache-key discipline",
        "seeding working memory at job start",
        "working-memory truncation strategies",
        "content-based chunking at section boundaries",
    ],
    "P6": [
        "loop anatomy: trigger, topology, verifier, stop rules",
        "the verifier as the bottleneck", "computational vs inferential verification",
        "LLM-as-judge pitfalls", "stop rules and iteration budgets",
        "the four nested loops", "hill-climbing the harness itself",
        "recoverable-error vs hard-blocker classification",
        "single-agent vs multi-agent tradeoffs", "org graphs vs work graphs",
        "typed handoff contracts", "policy routers",
        "fan-out and fan-in joins", "deterministic nodes vs agentic nodes",
        "human checkpoints as graph nodes", "context saturation",
        "unbounded delegation", "LangGraph state machines",
        "graph checkpointing and time travel", "the supervisor pattern critique",
        "swarm vs hierarchy topologies", "inter-agent message passing",
        "shared memory design", "subagent context isolation",
        "parallel agent worktrees", "merge and review gates",
        "the ADE taxonomy", "spec-approval gates", "task boards for agent fleets",
        "graph-level observability",
        "sequential subagents vs parallel agents",
        "gating on irreversibility, not importance",
        "over-gating and reviewer fatigue",
        "the four stop conditions: model, steps, wall-clock, tokens",
        "gates as graph nodes vs gates as model-called tools",
    ],
    "P7": [
        "eval-driven development", "unit evals vs end-to-end evals",
        "LLM-as-judge calibration", "golden datasets",
        "regression evals in CI", "A/B testing agent changes",
        "tracing agent runs", "correlated run and node identifiers",
        "token cost dashboards", "prompt drift detection",
        "canary deployments for prompts and models", "prompt and model versioning",
        "the prompt injection taxonomy", "least-privilege agent permissions",
        "data exfiltration risks", "PII handling in agent pipelines",
        "audit logging for agents", "red-teaming agent systems",
        "jailbreak resistance testing", "safety filter placement",
        "EU AI Act readiness", "incident response for AI systems",
        "hallucination measurement", "groundedness scoring",
        "cost regression gates", "SLOs for agent systems",
        "observability platform selection", "harnessability review checklists",
        "three-layer evaluation: harness, output, regression",
        "judge self-testing on known-good and known-bad outputs",
        "ship/revert margins for variant comparison",
        "cost per job as a first-class metric",
    ],
    "P8": [
        "Docker images for ML workloads", "Kubernetes GPU scheduling",
        "node pools and taints for GPU clusters", "MIG partitioning",
        "distributed training orchestration", "Ray cluster operations",
        "Airflow DAGs for data pipelines", "MLflow experiment tracking",
        "model registries", "feature stores", "TFX pipelines",
        "data validation gates", "concept drift monitoring",
        "data drift vs concept drift", "retraining triggers",
        "CI/CD for models", "blue-green model deployments",
        "shadow deployments", "artifact versioning with DVC",
        "GPU utilization monitoring", "spot instances and preemption handling",
        "checkpoint storage strategies", "vector database operations",
        "RAG pipeline infrastructure", "secrets management for ML stacks",
        "infrastructure-as-code for ML", "GPU FinOps and cost optimization",
        "capacity planning for training clusters",
    ],
    "P9": [
        "Netflix's recommendation architecture", "Airbnb search ranking",
        "DoorDash ETA prediction", "Uber's Michelangelo platform",
        "Spotify's recommendation stack", "Pinterest visual search",
        "Stripe's fraud detection ML", "LinkedIn feed ranking",
        "Instacart demand forecasting", "GitHub Copilot's serving architecture",
        "Klarna's support agent rollout", "enterprise RAG at scale",
        "why 95% of enterprise agents die in prototype",
        "coding-agent production postmortems", "fine-tune vs RAG decision cases",
        "LLM cost-reduction case studies", "edge AI deployment case studies",
        "multi-agent systems in production", "eval harness adoption stories",
        "monolith-to-services migration lessons",
        "scaling war stories from large tech companies",
        "production incident write-ups", "the Evidently AI case-study lineage",
        "ByteByteGo-style diagram breakdowns", "build vs buy for agent platforms",
    ],
    "P10": [
        "the FDE role anatomy", "FDE vs MLE vs AI engineer",
        "insights from 146 FDE job postings", "the AI system design interview format",
        "answering scaling questions", "whiteboard frameworks",
        "model-problem vs harness-problem diagnosis as a seniority signal",
        "take-home assignment strategy", "portfolio projects that signal seniority",
        "reading code as career leverage", "transitioning from data engineering",
        "transitioning from backend engineering", "transitioning from ML research",
        "leveling and compensation in AI infra", "company-by-company hiring loop data",
        "resumes for AI roles", "building in public", "open-source contribution strategy",
        "interview red flags", "mock interview drills", "negotiation for AI roles",
        "staying current systematically", "T-shaped skill development",
        "your first 90 days as an FDE",
    ],
}

# --------------------------------------------------------------------------
# Editorial passes: every pillar is revisited once per pass at a new angle
# --------------------------------------------------------------------------
ANGLES = [
    ("Foundations", "from first principles",
     "If the term is familiar but the mechanics are fuzzy, this pass is for you."),
    ("Builder's Pass", "by building it yourself",
     "Reading about it is not the same as building it. This pass, we build."),
    ("Failure Modes", "through how it breaks in production",
     "Everything breaks. This pass covers how this breaks and what the wreckage looks like."),
    ("Scale & Hardening", "at production scale",
     "What works in a demo dies at scale. This pass is about surviving contact with real traffic."),
    ("Frontier & Mastery", "at the frontier, interview-grade",
     "The difference between using a thing and being the person others ask about it."),
]

CTAS = [
    "Save this for your next design review.",
    "Repost this so your team sees it.",
    "Comment your take - I read every reply.",
    "Follow along - this series runs all week.",
    "Tag someone who is debugging this right now.",
    "Bookmark this; you will need it at 3am someday.",
]

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

FIELDNAMES = [
    "week", "date", "day", "slot", "time", "pillar", "weekly_theme",
    "editorial_angle", "format", "working_title", "hook", "outline",
    "cta", "source",
]


@dataclass
class Slot:
    week: int
    d: date
    day_name: str
    slot: str
    time: str


def _outline(*bullets: str) -> str:
    assert all(b.strip() for b in bullets), "empty outline bullet"
    return " | ".join(bullets)


def build_briefs(week: int, d: date, day_name: str, pillar_name: str,
                 theme: str, angle: tuple[str, str, str],
                 concepts: list[str], sources: list[str],
                 global_idx: int) -> list[dict]:
    """Return the AM and PM post briefs for one calendar day.

    concepts: the six concepts assigned to this week (Mon..Sat order).
    """
    angle_name, angle_qual, angle_line = angle
    src = sources[global_idx % len(sources)]
    cta = CTAS[global_idx % len(CTAS)]
    cta2 = CTAS[(global_idx + 3) % len(CTAS)]
    am: dict[str, str]
    pm: dict[str, str]

    if day_name == "Sunday":
        listed = "; ".join(concepts)
        am = {
            "format": "theme kickoff",
            "working_title": f"Week {week} kickoff - {theme}",
            "hook": f"This week: {pillar_name.lower()}, {angle_qual}. {angle_line}",
            "outline": _outline(
                f"Name the week's six topics: {listed}",
                "One sentence on why this pillar matters at this angle right now",
                "State what readers will be able to do by Saturday"),
        }
        pm = {
            "format": "poll",
            "working_title": f"Poll (week {week}): where are you with {pillar_name.lower()}?",
            "hook": "Quick pulse-check before the deep dives start tomorrow.",
            "outline": _outline(
                "Option A: learning the vocabulary",
                "Option B: built it once in a side project",
                "Option C: run it in production",
                "Option D: debugged it during an incident"),
        }
    elif day_name == "Monday":
        c = concepts[0]
        am = {
            "format": "concept deep-dive",
            "working_title": f"{c}, explained {angle_qual}",
            "hook": f"Most engineers can name {c}. Far fewer can explain the mechanics. Here is the {angle_name.lower()} version.",
            "outline": _outline(
                f"Define {c} in two sentences, no jargon",
                "Walk the core mechanism step by step with one concrete example",
                "State the one misconception that causes the most damage"),
        }
        pm = {
            "format": "annotated diagram",
            "working_title": f"{c} in one diagram ({angle_name.lower()})",
            "hook": f"If you cannot draw {c}, you do not understand it yet.",
            "outline": _outline(
                "Draw the components and the data flow between them",
                "Annotate the step where the interesting work happens",
                "Mark the failure point in red and say why it fails there"),
        }
    elif day_name == "Tuesday":
        c = concepts[1]
        am = {
            "format": "concept deep-dive",
            "working_title": f"The mental model for {c}, before the code ({angle_name.lower()})",
            "hook": f"Skip the diagram. Here's the problem {c} exists to solve, and the shape of the fix, before you read a line of code.",
            "outline": _outline(
                f"Define the failure {c} fixes, in two lines with a concrete example",
                "Build the mechanism conceptually, at the level of outcomes, not code",
                f"State what {c} still doesn't do, the gaps the code inherits"),
        }
        pm = {
            "format": "repo walkthrough",
            "working_title": f"Tracing the code that implements {c} ({angle_name.lower()})",
            "hook": f"The evening code half: the real implementation of {c} in {src}, read line by line.",
            "outline": _outline(
                f"Point to the exact file in {src} that implements {c} and read every line",
                "Trace one path through the code end to end, recomputing the real values",
                "Name the one line that is an honest tradeoff, not a bug"),
        }
    elif day_name == "Wednesday":
        c = concepts[2]
        am = {
            "format": "case study",
            "working_title": f"Case study: {c} in production ({angle_name.lower()})",
            "hook": f"A real team, a real system, and {c} under actual load. What happened next was predictable in hindsight.",
            "outline": _outline(
                "Set the scene: company scale, constraint, and why this concept was on the critical path",
                "Walk the decision, the implementation, and the number that moved",
                f"Close with the transferable rule about {c}"),
        }
        pm = {
            "format": "code deep-dive",
            "working_title": f"{c} in runnable code: the evening deep-dive ({angle_name.lower()})",
            "hook": f"The code behind the case study: a minimal, runnable model of {c} you can execute and verify.",
            "outline": _outline(
                f"Build a minimal runnable model of {c} from the morning's case study",
                "Annotate the two lines people get wrong",
                "State the expected output so readers can self-verify"),
        }
    elif day_name == "Thursday":
        c = concepts[3]
        am = {
            "format": "hands-on tutorial",
            "working_title": f"Hands-on: {c} in under an hour ({angle_name.lower()})",
            "hook": f"Stop reading about {c}. Here is the smallest real exercise that teaches it {angle_qual}.",
            "outline": _outline(
                "Define the end state: what exists and runs when the hour is up",
                "Give the 4-6 numbered steps with the commands or code per step",
                "Include the verification step that proves it worked"),
        }
        pm = {
            "format": "common mistakes checklist",
            "working_title": f"The {c} mistakes checklist ({angle_name.lower()})",
            "hook": f"Five checks that catch 90% of {c} mistakes before they ship.",
            "outline": _outline(
                f"Five yes/no checks phrased so 'no' means stop and fix, targeting mistakes made {angle_qual}",
                "For each: the symptom you will see in production if skipped",
                "Make it screenshot-able as a single card"),
        }
    elif day_name == "Friday":
        c = concepts[4]
        am = {
            "format": "contrarian take",
            "working_title": f"Hot take: most advice about {c} is wrong ({angle_name.lower()})",
            "hook": f"The standard advice on {c} optimizes for the demo, not the system you actually run.",
            "outline": _outline(
                "State the conventional wisdom fairly - steelman it in two lines",
                "Show the specific context where it fails and the evidence",
                "Give the replacement heuristic and its own limits"),
        }
        pm = {
            "format": "debate prompt",
            "working_title": f"Debate: is {c} necessary, or overengineering? ({angle_name.lower()})",
            "hook": f"Two senior engineers, opposite positions on {c}, both with production scars. Pick a side.",
            "outline": _outline(
                f"Present position A with its strongest supporting scenario, argued {angle_qual}",
                "Present position B with its strongest supporting scenario",
                "Ask readers to reply with their context - team size, scale, stakes"),
        }
    else:  # Saturday
        c = concepts[5]
        covered = "; ".join(concepts[:5])
        am = {
            "format": "recap + quiz",
            "working_title": f"Week {week} recap and quiz: {theme}",
            "hook": "Six days of material in three questions. Answers in Monday's post.",
            "outline": _outline(
                f"Recap in one line each: {covered}",
                "Three quiz questions: one recall, one application, one design tradeoff",
                "Invite answers in the comments; no lookups allowed"),
        }
        pm = {
            "format": "weekend challenge",
            "working_title": f"Weekend challenge: {c} ({angle_name.lower()})",
            "hook": f"90 focused minutes on {c} this weekend beats another saved-and-forgotten bookmark.",
            "outline": _outline(
                f"Define a scoped build/read exercise on {c}, {angle_qual}, with a visible artifact",
                f"Point to the exact starting resource: {src}",
                "Ask readers to post their artifact and tag it for review"),
        }

    base = {
        "week": str(week), "date": d.isoformat(), "day": day_name,
        "pillar": pillar_name, "weekly_theme": theme,
        "editorial_angle": angle_name,
    }
    am_row = {**base, "slot": "AM", "time": AM_TIME, **am, "cta": cta, "source": src}
    pm_row = {**base, "slot": "PM", "time": PM_TIME, **pm, "cta": cta2, "source": src}
    return [am_row, pm_row]


def build_week0() -> list[dict]:
    """Launch block for the gap days before the first Sunday: Thu-Sat, 2/day.

    Consolidation content: announce the series, walk the layer map, present
    the repo library, set the cadence, and baseline the audience so week 1
    starts on schedule with an oriented readership.
    """
    repo = "github.com/QuantumindSSI/systemdesign"
    specs = [
        (0, "AM", AM_TIME, "series announcement",
         "Announcing: 100 weeks of agentic + ML systems engineering, 2 posts a day",
         "~95% of enterprise agents die in prototype. Over the next 100 weeks I am publishing the dependency graph of skills that keeps yours out of that statistic - 2 posts a day, every day.",
         _outline(
             "State the thesis: agent skills form a dependency graph, and most engineers study the wrong layers",
             "Preview the 10 pillars in one line each, from system design fundamentals to career/FDE",
             "Set expectations: Sun-Sat cadence, fixed daily formats, first full week starts Sunday"),
         "Follow along - this series runs all week.", "curriculum.md (in " + repo + ")"),
        (0, "PM", PM_TIME, "poll",
         "Poll: which pillar should this series go deepest on?",
         "The calendar covers ten pillars over five passes. Vote for the one you want weighted heaviest - I will read the results before pass two.",
         _outline(
             "Option A: harness / loop / graph engineering",
             "Option B: inference and edge deployment",
             "Option C: system design fundamentals",
             "Option D: career, FDE and interviews"),
         "Comment your take - I read every reply.", "curriculum.md (in " + repo + ")"),
        (1, "AM", AM_TIME, "concept deep-dive",
         "The 7-layer map: why most engineers study the wrong layers",
         "Layer 0 knowledge is table stakes. Layers 2-4 are where agents live or die - and where almost nobody invests. Here is the full map.",
         _outline(
             "Walk Layers 0-6 in one line each: foundations, model lifecycle, agent stack, ADEs, evals/governance, MLOps, applied grounding",
             "Make the core claim: each layer assumes the one below it - skipping layers is how prototypes die",
             "Close with a self-diagnosis question: which layer is your weakest link right now?"),
         "Save this for your next design review.", "curriculum.md (in " + repo + ")"),
        (1, "PM", PM_TIME, "resource roundup",
         "The 28-repo reference library behind the next 100 weeks",
         "Every repo in this library was verified live this week - existence, activity, and content claims checked against each README. This is the source material for everything that follows.",
         _outline(
             "Present the six categories with one anchor repo each",
             "Explain the verification pass: what was checked and the one DMCA takedown it caught",
             "Link the full annotated list and invite readers to flag gaps"),
         "Bookmark this; you will need it at 3am someday.", "files.md (in " + repo + ")"),
        (2, "AM", AM_TIME, "how-it-works guide",
         "How this series works: the weekly cadence and the five passes",
         "Same rhythm every week for 100 weeks: kickoff Sunday, deep-dive Monday, real code Tuesday, case study Wednesday, hands-on Thursday, hot take Friday, quiz Saturday.",
         _outline(
             "Show the day-by-day format table for both daily slots",
             "Explain the five editorial passes: foundations, builder's pass, failure modes, scale, frontier",
             "Tell readers how to follow: daily at 09:00/17:00, or batch the week every Sunday"),
         "Follow along - this series runs all week.", "content_calendar_overview.md (in " + repo + ")"),
        (2, "PM", PM_TIME, "weekend challenge",
         "Weekend challenge: baseline yourself before week 1",
         "Before the first deep-dive lands Sunday, take 20 minutes to score yourself - honestly - across all ten pillars. You will revisit this baseline at week 20.",
         _outline(
             "Rate yourself 1-5 on each of the ten pillars and keep the scores somewhere visible",
             "Pick the pillar you are committing to move from a 2 to a 4 this year",
             "Post your weakest pillar in the comments - accountability beats bookmarks"),
         "Tag someone who is debugging this right now.", "curriculum.md (in " + repo + ")"),
    ]
    rows: list[dict] = []
    for day_off, slot, t, fmt, title, hook, outline, cta, src in specs:
        d = WEEK0_START + timedelta(days=day_off)
        rows.append({
            "week": "0", "date": d.isoformat(), "day": DAYS[(d.weekday() + 1) % 7],
            "slot": slot, "time": t, "pillar": "Series Launch",
            "weekly_theme": "Launch - consolidation before week 1",
            "editorial_angle": "Launch", "format": fmt, "working_title": title,
            "hook": hook, "outline": outline, "cta": cta, "source": src,
        })
    assert len(rows) == WEEK0_POSTS, "week 0 must contain exactly 6 posts"
    return rows


def generate() -> list[dict]:
    assert START_DATE.weekday() == 6, "start date must be a Sunday"
    assert len(PILLARS) == 10 and len(ANGLES) == 5, "5 passes x 10 pillars x 2 weeks = 100"
    for key, _, _ in PILLARS:
        assert len(CONCEPTS[key]) >= 13, f"{key} bank too small for angle rotation"

    rows: list[dict] = []
    concept_cursor = {key: 0 for key, _, _ in PILLARS}
    week = 0
    for pass_idx in range(5):
        angle = ANGLES[pass_idx]
        for pillar_idx in range(10):
            key, pillar_name, sources = PILLARS[pillar_idx]
            bank = CONCEPTS[key]
            for part in (1, 2):
                week += 1
                theme = f"{pillar_name} - {angle[0]}, part {part}"
                start = concept_cursor[key]
                week_concepts = [bank[(start + i) % len(bank)] for i in range(6)]
                concept_cursor[key] = (start + 6) % len(bank)
                week_start = START_DATE + timedelta(weeks=week - 1)
                for day_i in range(7):
                    d = week_start + timedelta(days=day_i)
                    rows.extend(build_briefs(
                        week, d, DAYS[day_i], pillar_name, theme, angle,
                        week_concepts, sources, global_idx=len(rows)))
    # Week 0 is prepended after the main build so weeks 1-100 keep the exact
    # rotation (and bytes) they had before the launch block existed.
    return build_week0() + rows


def validate(rows: list[dict]) -> None:
    expected = WEEKS * 7 * POSTS_PER_DAY + WEEK0_POSTS
    assert len(rows) == expected, f"expected {expected} rows, got {len(rows)}"
    titles = [r["working_title"] for r in rows]
    dupes = {t for t in titles if titles.count(t) > 1}
    assert not dupes, f"duplicate titles: {sorted(dupes)[:5]}"
    assert rows[0]["date"] == WEEK0_START.isoformat(), "week 0 must start 2026-08-20"
    assert rows[0]["day"] == "Thursday", "week 0 must start on a Thursday"
    assert rows[WEEK0_POSTS]["date"] == START_DATE.isoformat(), "week 1 must start on START_DATE"
    assert rows[WEEK0_POSTS]["day"] == "Sunday", "week 1 must start on a Sunday"
    expected_end = START_DATE + timedelta(days=WEEKS * 7 - 1)
    assert rows[-1]["date"] == expected_end.isoformat(), "wrong end date"
    for r in rows:
        for f in FIELDNAMES:
            assert str(r[f]).strip(), f"empty field {f} in row dated {r['date']}"
    per_week: dict[str, int] = {}
    for r in rows:
        per_week[r["week"]] = per_week.get(r["week"], 0) + 1
    assert per_week.pop("0") == WEEK0_POSTS, "week 0 must have 6 posts"
    assert all(v == 14 for v in per_week.values()), "weeks 1-100 must have 14 posts each"


PUBLISHING_FORMAT = """\
## Publishing format (effective 2026-08-24, week 1 onward)

Platform is Substack, not LinkedIn. Each calendar day produces three artifacts,
not one post per slot:

### Human-first voice (required)

Every reader-facing essay and follow-up must feel like a conversation with a
thoughtful person, not a detached technical reference. Open with a natural
greeting, check-in, or familiar everyday moment. Carry that relationship
through every major section with reader-facing transitions and concrete daily
analogies; do not confine the human voice to the introduction. Explain the
precise technical mechanism immediately after each relatable frame, without
weakening sourced claims or numerical rigor. Close by reconnecting the lesson
to a decision, problem, or experience the reader is likely to recognize. Keep
the warmth natural: do not invent personal stories, force slang, or repeat the
same greeting mechanically.

- **09:00 - the essay.** A full long-form Substack essay, 2,500-3,500 words.
  The day's `format` column (concept deep-dive, repo walkthrough, case study,
  etc.) is not a separate short post; it is the essay's spine, the structural
  backbone the essay is organized around. A "concept deep-dive" essay leads
  with a plain-language definition, walks the mechanism with a concrete
  example, and closes on the load-bearing misconception. A "case study" essay
  leads with the scene, walks the decision and the numbers, and closes on the
  transferable rule. The outline column in the CSV names the spine's beats;
  the essay fills each beat out to full depth rather than one sentence.
- **17:00 - the follow-up or code deep-dive.** Built around that day's PM
  `format` column, same day and same underlying example as the morning, never
  a new topic. On most days it is a short 500-700 word reinforcement of one
  piece of the essay (an annotated diagram, a checklist, and so on). On
  Tuesday and Wednesday the evening slot is instead a full code companion to
  the morning's concept: Tuesday walks the real implementation line by line
  (repo walkthrough), Wednesday builds a runnable model from the case study
  (code deep-dive). Either way it assumes the reader has read the 09:00 essay.
- **Teasers, one file, four platforms.** A short comment-length teaser for
  Twitter/X, LinkedIn, Reddit, and Quora, each in that platform's native
  voice and length convention, each linking back to the Substack essay. These
  replace the old full-repost "publish cut": the essay lives on Substack,
  the other platforms only ever get a hook and a link, never the full text.

File naming for each day: `posts/{date}-{day}-am-essay-{slug}.md` (the
essay), `posts/{date}-{day}-pm-followup-{slug}.md` (the buttressing
follow-up), `posts/{date}-{day}-teasers.md` (the four-platform bundle). Each
essay and follow-up file carries an editorial audit header (source
verification, numbers audit) above a `---` marker; only the content below
that marker is the reader-facing publish copy."""


def write_outputs(rows: list[dict], out_dir: str) -> tuple[str, str]:
    csv_path = os.path.join(out_dir, "content_calendar.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    md_path = os.path.join(out_dir, "content_calendar_overview.md")
    end = START_DATE + timedelta(days=WEEKS * 7 - 1)
    spans: dict[str, tuple[str, str, str, str]] = {}
    for r in rows:
        first, _, pillar, angle = spans.get(
            r["week"], (r["date"], r["date"], r["pillar"], r["editorial_angle"]))
        spans[r["week"]] = (first, r["date"], pillar, angle)
    weeks_index = [
        f"| {wk} | {first} - {last} | {pillar} | {angle} |"
        for wk, (first, last, pillar, angle) in spans.items()
    ]
    total = WEEKS * 7 * POSTS_PER_DAY + WEEK0_POSTS
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join([
            "# Content Calendar - System Overview",
            "",
            f"**{total} posts** - a 6-post launch block (week 0: Thu {WEEK0_START.isoformat()} "
            f"to Sat), then 2/day (09:00 + 17:00), Sun-Sat, for {WEEKS} weeks: "
            f"{START_DATE.isoformat()} to {end.isoformat()}.",
            "",
            "Full calendar: `content_calendar.csv` (one complete brief per post: title, "
            "hook, 3-bullet outline, CTA, source). Regenerate or re-date by editing "
            "`generate_calendar.py` (set `START_DATE`) and rerunning - output is deterministic.",
            "",
            "## How the system works",
            "",
            "- **10 pillars** drawn from `curriculum.md` (Layers 0-6) and `files.md` (28 verified repos).",
            "- **`resources_by_week.md`**: further-reading pool for article generation, one section per calendar week, ranked from a 1,807-resource scrape (papers, code, docs, courses) against that week's theme and hooks. Generated by `mlsource/tools/build_topic_index.py`; regenerate after editing the calendar or the corpus. Coverage varies by pillar (the source scrape skews technical/research, so Career/FDE weeks return thinner matches than System Design or LLM Internals weeks) - treat it as a candidate pool to filter while writing, not a final source list.",
            "- **5 editorial passes x 20 weeks**: Foundations -> Builder's Pass -> Failure Modes -> "
            "Scale & Hardening -> Frontier & Mastery. Every pillar gets 2 weeks per pass.",
            "- **Concepts recur across passes by design** (pillar-cluster model) but never with the "
            "same angle + format; all 1,400 titles are asserted unique at generation time.",
            "- **Fixed daily cadence** so production becomes routine:",
            "",
            "| Day | 09:00 | 17:00 |",
            "|---|---|---|",
            "| Sun | Theme kickoff | Poll |",
            "| Mon | Concept deep-dive | Annotated diagram |",
            "| Tue | Concept deep-dive | Repo walkthrough |",
            "| Wed | Case study | Code deep-dive |",
            "| Thu | Hands-on tutorial | Mistakes checklist |",
            "| Fri | Contrarian take | Debate prompt |",
            "| Sat | Recap + quiz | Weekend challenge |",
            "",
            PUBLISHING_FORMAT,
            "",
            "## Working the calendar",
            "",
            "1. Batch-write one week (14 briefs) in a single sitting; the briefs are complete outlines.",
            "2. The CSV imports directly into Notion, Google Sheets, Airtable, or Buffer/Hypefury.",
            "3. Swap any concept by editing its pillar bank in the generator and rerunning.",
            "4. Numerical grounding rule: every number in a published post must name its source "
            "inline, be explicitly flagged as unaudited at the point of use, or be cut "
            "(QSSI research persona, Amendment 1).",
            "",
            "## 100-week index",
            "",
            "| Week | Dates | Pillar | Pass |",
            "|---|---|---|---|",
            *weeks_index,
            "",
        ]))
    return csv_path, md_path


def main() -> int:
    out_dir = os.path.dirname(os.path.abspath(__file__))
    rows = generate()
    validate(rows)
    csv_path, md_path = write_outputs(rows, out_dir)
    uniq_concepts = sum(len(v) for v in CONCEPTS.values())
    print(f"OK: {len(rows)} post briefs -> {csv_path}")
    print(f"OK: overview + 100-week index -> {md_path}")
    print(f"Range: {rows[0]['date']} ({rows[0]['day']}) -> {rows[-1]['date']} ({rows[-1]['day']})")
    print(f"Concept bank: {uniq_concepts} concepts across {len(PILLARS)} pillars; "
          f"all titles unique: True")
    return 0


if __name__ == "__main__":
    sys.exit(main())
