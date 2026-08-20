# System Design & LLM Engineering — Repo Reference

28 repositories across six categories: system design fundamentals, LLM pretraining, post-training/alignment, inference engineering, agent & harness engineering, and production ML engineering.

*All links verified live on 2026-08-20 — existence, activity, and content claims checked against each repo's README. One removal noted at the bottom.*

## System Design Fundamentals

- [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) — the canonical fundamentals reference: scalability vs. performance, CAP theorem, caching, load balancing, DB scaling, plus worked interview questions.
- [ByteByteGoHq/system-design-101](https://github.com/ByteByteGoHq/system-design-101) — visual, diagram-heavy explainers of core architecture patterns. Good for fast intuition or pulling clean diagrams into decks.
- [karanpratapsingh/system-design](https://github.com/karanpratapsingh/system-design) ("System Design at Scale") — a structured, course-like walkthrough of distributed systems, scaling techniques, and real-world examples rather than a link dump.
- [ashishps1/awesome-system-design-resources](https://github.com/ashishps1/awesome-system-design-resources) — actively maintained curated list of high-quality articles/videos across system design domains; good navigational hub.
- [binhnguyennus/awesome-scalability](https://github.com/binhnguyennus/awesome-scalability) ("Scalability Engineering") — real-world scale-out case studies and performance-engineering principles from large tech companies; complementary to the ML case-study repo.
- [themanojdesai/genai-llm-ml-case-studies](https://github.com/themanojdesai/genai-llm-ml-case-studies) — 500+ case studies specifically on production GenAI/LLM systems (RAG, fine-tuning, agents) from 100+ companies; builds on Evidently AI's original list and is more current/agent-relevant than the Engineer1999 repo.
- [Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies](https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies) — 300+ pre-LLM-era ML system design case studies from 80+ companies (Netflix, Airbnb, DoorDash); the classic-ML complement to the GenAI case-study repo above.
- [checkcheckzz/system-design-interview](https://github.com/checkcheckzz/system-design-interview) — structured answer frameworks for system design interviews (static content, unmaintained since 2023).
- [chiphuyen/machine-learning-systems-design](https://github.com/chiphuyen/machine-learning-systems-design) — Chip Huyen's booklet on ML systems design with exercises; note it is explicitly *not* the "Designing Machine Learning Systems" book (that companion repo is `dmls-book`).

## LLM Pretraining / From Scratch

- [karpathy/nanochat](https://github.com/karpathy/nanochat) — Karpathy's minimal, readable full pipeline: tokenization → pretraining → finetuning → eval → inference → chat UI, runs on a single GPU node. Best single repo for building real intuition below the API layer.
- [rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch) — companion code to Raschka's book; GPT-like model built and pretrained from scratch in PyTorch, now includes from-scratch Llama/Qwen/Gemma implementations and modern attention variants (GQA, MLA, sliding-window, DeepSeek Sparse Attention, MoE).
- [RUCAIBox/awesome-llm-pretraining](https://github.com/RUCAIBox/awesome-llm-pretraining) — curated index of pretraining data, frameworks (TorchTitan), and methods: scaling laws, parallelism strategies, FP8 training, optimizer choice.
- [FareedKhan-dev/train-llm-from-scratch](https://github.com/FareedKhan-dev/train-llm-from-scratch) — the full journey in one place: raw text → tokens → transformer → base model → SFT → reward model → PPO/DPO → GRPO, hand-written with a theory write-up per stage.

## Post-training / Alignment / RL

- [huggingface/trl](https://github.com/huggingface/trl) — the standard post-training library: SFT, PPO, GRPO, DPO, reward modeling, built on the Transformers ecosystem.
- [mbzuai-oryx/Awesome-LLM-Post-training](https://github.com/mbzuai-oryx/Awesome-LLM-Post-training) — survey/tutorial index specifically for the post-training stage: RLHF frameworks, DPO variants, reasoning-model training.
- [OpenRLHF/OpenRLHF](https://github.com/OpenRLHF/OpenRLHF) — high-performance RLHF framework built on Ray + vLLM + ZeRO-3, closer to what production alignment pipelines actually look like at scale.
- [hiyouga/LlamaFactory](https://github.com/hiyouga/LlamaFactory) (renamed from LLaMA-Factory) — unified fine-tuning across 100+ models: pretraining, SFT, reward modeling, PPO/DPO/ORPO, LoRA/QLoRA, with vLLM-backed serving built in — good bridge repo between post-training and deployment.

## Inference Engineering

*Given your edge AI hardware focus, this is probably your highest-leverage category.*

- [vllm-project/vllm](https://github.com/vllm-project/vllm) — the reference high-throughput serving engine: PagedAttention, FP8/INT4 quantization, speculative decoding, OpenAI-compatible API. Default for GPU serving at scale.
- [NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) — kernel-level, graph-level optimization for NVIDIA hardware; lowest time-to-first-token; covers disaggregated prefill/decode serving, directly relevant to Victron/Athenoir-style hardware-aware inference work.
- [xlite-dev/Awesome-LLM-Inference](https://github.com/xlite-dev/Awesome-LLM-Inference) — curated papers+code on inference optimization: FlashAttention, PagedAttention, quantization (WINT8/4), parallelism strategies.
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) — the standard for CPU/edge/on-device inference with quantized GGUF models; most directly applicable to sovereign edge AI deployment.

## Agent & Harness Engineering

*Maps to Layers 2.3–2.5 of the curriculum: harness → loop → graph.*

- [ai-boost/awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering) — awesome list for AI agent harness engineering: tools, patterns, evals, memory, MCP, permissions, observability, and orchestration.
- [DenisSergeevitch/agents-best-practices](https://github.com/DenisSergeevitch/agents-best-practices) — provider-neutral agent skill and best practices for Codex, Claude Code, and agentic harness design.
- [cobusgreyling/loop-engineering](https://github.com/cobusgreyling/loop-engineering) — practical patterns, starters, and CLI tools (`loop-audit`, `loop-init`, `loop-cost`) for loop engineering: designing the systems that prompt and orchestrate coding agents, verifier and stop-rule design included.
- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) — low-level orchestration framework for stateful multi-agent systems as graphs; the reference implementation for the org-graph/work-graph decomposition in the curriculum's graph engineering layer.

## Production ML Engineering / FDE

- [alexeygrigorev/ai-engineering-field-guide](https://github.com/alexeygrigorev/ai-engineering-field-guide) — research into FDE role scope from 146 real job postings, AI system design interview patterns, and transition paths from adjacent roles (ML engineer, data engineer).
- [ai-infra-curriculum/ai-infra-engineer-learning](https://github.com/ai-infra-curriculum/ai-infra-engineer-learning) — production ML infra curriculum: Docker/K8s/GPU scheduling, MLOps pipelines (Airflow, MLflow), distributed training, LLM infra (vLLM, RAG, vector DBs), monitoring/observability.
- [amanchadha/coursera-machine-learning-engineering-for-prod-mlops-specialization](https://github.com/amanchadha/coursera-machine-learning-engineering-for-prod-mlops-specialization) — assignments covering the full production ML lifecycle: data pipelines, TFX feature engineering, concept drift, deployment — useful for the "boring but essential" MLOps gaps that pure LLM repos skip.

---

**Removed:** `sarwarbeing-ai/Agentic_Design_Patterns` — repository blocked on GitHub via DMCA takedown (Springer, Feb 2026). Public mirrors of the same book content carry identical takedown exposure, so no replacement link; the Agent & Harness Engineering section above covers the same ground with original material.
