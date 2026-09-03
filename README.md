# Sustainable Packaging Multi-Agent Platform 🌱📦

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Architecture](https://img.shields.io/badge/Architecture-Microservices-orange)
![Agent Framework](https://img.shields.io/badge/Agents-Agno%20%7C%20LangGraph-green)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)

An enterprise-grade, multi-agent orchestration platform designed to automate the evaluation, compliance, and selection of sustainable packaging materials. Powered by Google Gemini, LangGraph, and a highly scalable background execution model.

## 🎯 Overview

Transitioning from prototype to a production-ready SaaS backend, this platform leverages a **Dynamic Agent Registry** and a **Fact Broker** to provide evidence-based, region-specific packaging recommendations. It evaluates materials across environmental impact, logistics, cost, consumer behavior, and regulatory compliance without hallucinating facts.

## 🏗️ Architecture

The system is built on a distributed microservices architecture to ensure non-blocking UI interactions, durable state persistence, and cost-effective LLM invocations.

### Core Components
1. **Frontend (React & Vite)**: A premium, highly responsive UI (`frontend/src/App.tsx`) built with React and Tailwind-like Vanilla CSS. It offloads heavy analysis to the FastAPI backend.
2. **Backend API (FastAPI)**: Exposes REST endpoints (`api/main.py`) to handle incoming analysis parameters and BOM uploads, delegating execution to the task queue.
3. **Task Queue (Celery & Redis)**: Long-running LangGraph executions are enqueued as asynchronous Celery tasks (`libs/shared/tasks.py`), backed by Redis.
4. **Orchestrator (LangGraph & Postgres)**: The state machine (`main.py`) controls agent flow. It uses `AsyncPostgresSaver` to persist intermediate states.
4. **Dynamic Agent Registry (`libs/shared/registry.py`)**: Unlike fixed fan-out models, the registry routes graph execution *only* to agents whose trigger conditions are met (e.g., ESG reporting flags). This strictly bounds token usage.
5. **Fact Broker MCP**: A unified data layer that provides cached, authoritative grounding (EUR-Lex, DEFRA, Open Food Facts) to prevent LLM hallucinations.

### The Agent Roster
The platform executes in a two-stage fan-out:
- **Phase 1 Analysts**: `MaterialProperties`, `Logistics`, `ProductionCost`, `Sustainability`, `ConsumerBehavior`.
- **Phase 2 Synthesis**: `CarbonLcaService` (kg-CO2e deltas) and `ComplianceDocService` (PPWR Declaration of Conformity).

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Google Gemini API Key

### Installation & Execution
1. Clone the repository:
   ```bash
   git clone https://github.com/codegeek03/Multi_Agent_Architecture_for_Sustainable_Packaging.git
   cd Multi_Agent_Architecture_for_Sustainable_Packaging
   ```
2. Configure Environment:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY to the .env file
   ```
3. Boot the Infrastructure:
   ```bash
   docker-compose up --build
   ```
   This spins up:
   - `redis` (Message Broker)
   - `postgres` (State Checkpointing & Fact Broker Cache)
   - `celery_worker` (Background Execution)
   - `web` (Streamlit UI on `http://localhost:8501`)

4. Navigate to `http://localhost:8501` to start your packaging analysis.

## 🛡️ DevOps & LLMOps

This repository enforces strict engineering operations tailored for LLM applications:
- **Continuous Integration (`.github/workflows/ci.yml`)**: Blocks merges that fail linting (`ruff`, `mypy`), security checks (`pip-audit`, `gitleaks`), or unit tests.
- **LLM Eval Harness**: Prompts are tested against a golden set (`libs/shared/eval/evaluator.py`) using LLM-as-a-judge to catch silent output degradation before deployment.
- **Observability**: Fully structured JSON logging (`python-json-logger`) and integrated `sentry-sdk` for production error tracking.
- **Architecture Decision Records (ADRs)**: Crucial engineering decisions are documented in `docs/adr/`.

## 📂 Repository Structure

```text
├── agents/                 # Legacy/Utility input agents
├── libs/shared/            # Core schemas, registry, celery tasks, and LLM evals
├── services/               # Microservices representing each specialized Agent
├── prompts/                # Versioned XML-structured system prompts
├── docs/adr/               # Architecture Decision Records
├── tests/                  # Unit and Contract tests (Pydantic schema validation)
├── app.py                  # Streamlit Web UI
├── main.py                 # LangGraph Orchestrator definitions
├── docker-compose.yml      # Infrastructure topology
└── Dockerfile              # Unified application container
```

## 🤝 Contributing
1. Create a feature branch off `main`.
2. Ensure your changes pass the CI pipeline (especially the Pydantic contract tests and LLM eval harness).
3. Submit a Pull Request for review.

## 📄 License
This project is licensed under the MIT License.
