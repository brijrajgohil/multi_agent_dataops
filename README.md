# AI DataOps Incident Agent

A local-first incident investigation app for data pipeline failures and metric anomalies.

## Repository Structure

```text

│   ├── logs/           # Pipeline log files
│   ├── metadata/       # Freshness, lineage, schema metadata
│   ├── runbooks/       # Markdown troubleshooting runbooks
│   ├── traces/         # JSONL workflow traces
│   └── warehouse/      # DuckDB warehouse file
├── docs/
│   └── steps.md        # Phase-by-phase implementation plan
├── src/
│   ├── agents/         # Triage, investigation, resolution agents
│   ├── app/            # FastAPI app
│   ├── evals/          # Eval runner and metrics
│   ├── evidence/       # File-backed evidence store
│   ├── guardrails/     # Input, tool, output guardrails
│   ├── llm/            # Local Llama client and prompts
│   ├── tools/          # MCP server/client and deterministic tools
│   ├── tracing/        # JSONL trace logger
│   ├── workflow/       # Workflow state and orchestration
│   └── config.py
├── streamlit_app/
│   └── app.py          # Streamlit UI
├── tests/
└── requirements.txt
```

## Install Dependencies

```bash
python -m pip install -r requirements.txt
```

Optional virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy the sample configuration:

```bash
cp .env.example .env
```

## Run FastAPI

```bash
python -m uvicorn src.app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Submit an incident:

```bash
curl -X POST http://127.0.0.1:8000/incidents/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Revenue dropped by 40% in the daily dashboard. Please investigate.",
    "metric_name": "revenue",
    "dashboard_name": "daily_revenue_dashboard",
    "severity": "high"
  }'
```

Fetch trace records:

```bash
curl http://127.0.0.1:8000/incidents/<incident_id>/trace
```

Fetch evidence records:

```bash
curl http://127.0.0.1:8000/incidents/<incident_id>/evidence
```

## Run Streamlit

```bash
DATAOPS_API_BASE_URL=http://127.0.0.1:8000 \
python -m streamlit run streamlit_app/app.py --server.port 8501
```

Open:

```text
http://127.0.0.1:8501
```

## MCP Tool Server

The application starts the MCP server through the local MCP client over `stdio`.

Manual server check:

```bash
python -m src.tools.mcp_server
```

The process waits for MCP `stdio` messages. Stop it with `Ctrl+C`.


## Command Summary

```bash
python -m pip install -r requirements.txt
python -m uvicorn src.app.main:app --host 127.0.0.1 --port 8000
DATAOPS_API_BASE_URL=http://127.0.0.1:8000 python -m streamlit run streamlit_app/app.py
```
