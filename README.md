# Agent Infrastructure — Distributed AI Agent System

**Stack:** Kafka · Weaviate · DSPy · MCP · AKS · Anthropic Claude

A multi-agent system where specialized AI agents collaborate to complete complex tasks via async Kafka messaging, semantic memory in Weaviate, and DSPy-optimized prompts.

---

## Architecture

```
User Goal
    │
    ▼
[Planner Agent] ──── tasks.assigned ────► [Executor Agent(s)]
    │                                           │
    │                                    tasks.completed
    │                                           │
    └── Weaviate (memory) ◄──────────────────────┘
              ▲
          DSPy tunes prompts for both agents
```

**Phase 1 (this branch):** Planner + Executor over Kafka + Weaviate memory  
**Phase 2:** Critic + Summarizer agents  
**Phase 3:** MCP server exposing agent tools  
**Phase 4:** DSPy optimization loop + AKS deployment  

---

## Setup

### 1. Clone and install

```bash
git clone <repo>
cd agent-infra
poetry install
cp .env.example .env
# fill in ANTHROPIC_API_KEY and OPENAI_API_KEY in .env
```

### 2. Start infrastructure

```bash
docker compose up -d
```

Services:
- Kafka → `localhost:9092`
- Kafka UI → `http://localhost:8090`
- Weaviate → `http://localhost:8080`

### 3. Run the agents (3 separate terminals)

```bash
# Terminal 1 — Planner
poetry run python -m agents.planner.agent

# Terminal 2 — Executor (run 2+ for parallelism)
poetry run python -m agents.executor.agent

# Terminal 3 — Submit a goal and watch results
poetry run python cli.py "Find the top 5 ML papers from the last month and summarize their key contributions"
```

---

## Project Structure

```
agent-infra/
├── agents/
│   ├── planner/agent.py      # Decomposes goals → publishes tasks
│   └── executor/agent.py     # Consumes tasks → executes → publishes results
├── core/
│   ├── models.py             # Pydantic models: Goal, Task, TaskResult
│   ├── kafka.py              # KafkaPublisher, KafkaConsumerLoop, ensure_topics
│   ├── memory.py             # Weaviate episodic memory client
│   └── dspy_modules.py       # DSPy signatures: PlannerModule, ExecutorModule
├── config/
│   └── topics.py             # Kafka topic definitions
├── cli.py                    # Submit goals + tail results
├── docker-compose.yml        # Kafka + Weaviate + Kafka UI
├── pyproject.toml
└── .env.example
```

---

## Kafka Topics

| Topic | Published by | Consumed by |
|---|---|---|
| `goals.submitted` | CLI / external | Planner |
| `tasks.assigned` | Planner | Executor |
| `tasks.completed` | Executor | Critic (Phase 2) |
| `tasks.rejected` | Critic (Phase 2) | Executor |
| `tasks.approved` | Critic (Phase 2) | Summarizer (Phase 2) |

---

## Resume Metrics to Track

Run experiments and record:
- Tasks processed per second (Executor throughput)
- End-to-end latency: goal submitted → all tasks completed
- Memory hit rate: % of tasks where past context was found
- DSPy prompt improvement (Phase 4): quality score before vs after optimization

---

## What's Next (Phase 2)

- `agents/critic/agent.py` — evaluates TaskResults, publishes approved/rejected
- `agents/summarizer/agent.py` — aggregates approved results into final answer
- Weaviate collection for goal-level result aggregation
