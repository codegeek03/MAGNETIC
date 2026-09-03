# ADR 0001: Dynamic Agent Registry for Workflow Routing

## Status
Accepted

## Context
The initial prototype used a fixed parallel fan-out architecture in LangGraph: every analysis request triggered all 5 analyst agents simultaneously. As the agent roster grows (e.g., adding Carbon LCA or specific compliance checks), running every agent on every request becomes computationally wasteful and financially expensive due to LLM API costs. Furthermore, many specialized agents (like Hazmat Classification) are only relevant for a subset of queries.

## Decision
We implemented a **Dynamic Agent Registry** (`libs/shared/registry.py`) that decouples agents from hardcoded graph edges.
1. Agents register themselves with a specific execution phase and a lambda function (trigger condition) that evaluates the input state.
2. The LangGraph orchestration uses the `Send` API to dynamically route execution only to the agents whose trigger conditions return `True`.

## Consequences
**Pros:**
- Significantly reduces LLM API costs by pruning irrelevant agent invocations.
- Enables safely adding niche/domain-specific agents without affecting the baseline execution latency.
- Enforces strict execution phase ordering (e.g., Phase 2 agents can consume Phase 1 outputs).

**Cons:**
- Increased complexity in tracing execution paths, as the graph topology is determined at runtime rather than statically defined.
