## Data Visualizer

A [pixi](https://pixi.sh)-based [Streamlit](https://streamlit.io) app that lets you upload a CSV and explore it through interactive [Plotly](https://plotly.com/python/) charts. Build charts manually with a point-and-click interface, or describe what you want in plain English and let a local LLM generate the visualization.

Requires: `pixi` ([install](https://pixi.sh/latest/#installation))

To launch just the Data Visualizer app:
```bash
pixi run launch
```

Streamlit listens on `http://localhost:8501` by default.

To start both the Data Visualizer and the companion `llamacpp` server simultaneously:
```bash
python run_both.py
```

### Workflow

1. Upload a CSV in Settings — or click **Load sample data** to load the bundled `sample_orders.csv` (120 rows of synthetic e-commerce orders) for a quick demo.
2. Use the **Chart Builder** tab to instantly create charts by picking a chart type, axes, aggregation, and grouping.
3. Use the **AI Chart** tab to describe a visualization in plain English — the LLM generates and runs Plotly code, and shows you the result alongside the code it wrote.
4. Use the **Data** tab to inspect the raw table and column schema.

### Chart Builder

The Chart Builder supports eight chart types:

| Chart type | Best for |
|---|---|
| Bar | Comparing totals or aggregates across categories |
| Line | Trends over time or an ordered axis |
| Area | Cumulative trends over time |
| Scatter | Relationships between two numeric variables |
| Histogram | Distribution of a single numeric variable |
| Box | Spread and outliers across groups |
| Pie | Part-to-whole composition |
| Correlation Heatmap | Pairwise correlation between all numeric columns |

Controls adapt to the selected chart type — only relevant columns and options are shown.

### AI Chart

The AI Chart tab sends your request to a local (or remote) LLM along with the DataFrame schema and a 10-row sample. The model returns Python code using `plotly.express` or `plotly.graph_objects`; the app executes it and renders the figure. The generated code is shown in a collapsible expander below each chart.

Pick a provider and click **Scan for running models** in Settings before using AI Chart.

> ⚠ **Picking the remote provider sends your data off this device** — the schema and 10-row sample will be transmitted to whatever API host you point it at. Use a local provider if your CSV contains anything sensitive.

### Supported providers

| Provider | Default URL | Model discovery endpoint | OpenAI base URL | API key |
|---|---|---|---|---|
| llama.cpp | `http://localhost:8080` | `GET /v1/models` | `/v1` | — |
| Ollama | `http://localhost:11434` | `GET /api/tags` | `/v1` | — |
| Docker Model Runner | `http://localhost:12434` | `GET /engines/v1/models` | `/engines/v1` | — |
| Remote (OpenAI-compatible) | `https://api.openai.com/v1` | `GET /models` | (base URL itself) | required |

### Companion capabilities

- The [`llamacpp`](../llamacpp) capability in this repo runs a llama.cpp server on `http://localhost:8080` — start it (`pixi run serve` or `pixi run -e gpu serve`) and Data Visualizer's default llama.cpp settings will Just Work.
- The [`data-explorer`](../data-explorer) capability lets you chat with the same CSV data if you prefer a text-based Q&A workflow alongside visualization.
- For Ollama, install [Ollama](https://ollama.com) and `ollama pull` any model.
- For Docker Model Runner, enable Model Runner in Docker Desktop settings and `docker model pull <model>`.
