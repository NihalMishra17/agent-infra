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

### 3. Run the agents (one terminal each)

```bash
# Terminal 1 — Planner
python -m agents.planner.agent

# Terminal 2 — Executor (run 2+ for parallelism)
python -m agents.executor.agent

# Terminal 3 — Critic
python -m agents.critic.agent

# Terminal 4 — Summarizer
python -m agents.summarizer.agent

# Terminal 5 — Submit a goal and watch results
python cli.py "Find the top 5 ML papers from the last month and summarize their key contributions"
```

---

## Project Structure

```
agent-infra/
├── agents/
│   ├── planner/agent.py      # Decomposes goals → publishes tasks + GoalPlan
│   ├── executor/agent.py     # Executes tasks, retries on critic rejection
│   ├── critic/agent.py       # Scores results (1-10), routes approved/rejected
│   └── summarizer/agent.py  # Synthesizes approved results into final answer
├── core/
│   ├── models.py             # Pydantic models: Goal, Task, TaskResult, CriticFeedback, GoalPlan, FinalSummary
│   ├── kafka.py              # KafkaPublisher, KafkaConsumerLoop, ensure_topics
│   ├── memory.py             # Weaviate episodic memory client
│   └── dspy_modules.py       # DSPy: PlannerModule, ExecutorModule, CriticModule, SummarizerModule
├── mcp_server/
│   └── server.py             # MCP stdio server exposing agent tools to Claude Desktop
├── config/
│   └── topics.py             # Kafka topic definitions
├── cli.py                    # Submit goals + stream results + print final summary
├── docker-compose.yml        # Kafka + Weaviate + transformers inference
├── pyproject.toml
└── .env
```

---

## Kafka Topics

| Topic | Published by | Consumed by |
|---|---|---|
| `goals.submitted` | CLI / MCP server | Planner |
| `goals.planned` | Planner | Summarizer |
| `goals.summarized` | Summarizer | CLI |
| `tasks.assigned` | Planner | Executor |
| `tasks.completed` | Executor | Critic |
| `tasks.rejected` | Critic | Executor (retry) |
| `tasks.approved` | Critic | Summarizer |

---

## Phase 3 — MCP Server

The MCP server exposes the agent pipeline as tools callable from Claude Desktop
or any MCP-compatible client.

### Running the server

```bash
python -m mcp_server.server
```

It communicates over stdio (no port needed).

### Tools

| Tool | Description |
|---|---|
| `submit_goal` | Publish a goal to the pipeline, returns `goal_id` |
| `get_goal_status` | Count Weaviate memory entries per agent for a goal |
| `search_memory` | Semantic search over all episodic memory |
| `get_final_summary` | Retrieve the synthesized final answer for a completed goal |

### Connecting to Claude Desktop

Add the following to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agent-infra": {
      "command": "/Users/nihal/Library/Caches/pypoetry/virtualenvs/agent-infra-tkrHu4Kp-py3.12/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/Users/nihal/agent-infra",
      "env": {
        "ANTHROPIC_API_KEY": "<your-key>",
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "WEAVIATE_HOST": "localhost",
        "WEAVIATE_PORT": "8080"
      }
    }
  }
}
```

After saving, restart Claude Desktop. The four agent-infra tools will appear
in the tools panel. Make sure `docker compose up -d` is running and at least
the Planner, Executor, Critic, and Summarizer agents are active before
calling `submit_goal`.

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
