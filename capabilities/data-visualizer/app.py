"""Data Visualizer — upload a CSV and build interactive charts, or describe charts in plain English.

Two modes:
- Chart Builder: pick chart type, axes, and aggregation for an instant Plotly chart.
- AI Chart: describe a visualization in plain text; the LLM generates and renders Plotly code.

Supports llama.cpp, Ollama, Docker Model Runner, and any OpenAI-compatible API.
"""
from __future__ import annotations

import io
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generator

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# (key, display label) pairs — order determines the selectbox order.
CHART_TYPES: list[tuple[str, str]] = [
    ("bar",       "Bar"),
    ("line",      "Line"),
    ("area",      "Area"),
    ("scatter",   "Scatter"),
    ("histogram", "Histogram"),
    ("box",       "Box"),
    ("pie",       "Pie"),
    ("heatmap",   "Correlation Heatmap"),
]
CHART_TYPE_LABELS: dict[str, str] = dict(CHART_TYPES)

AGG_FUNCS: list[str] = ["sum", "mean", "count", "min", "max", "median"]

# Applied to every rendered figure for consistent spacing.
_CHART_MARGIN = dict(margin=dict(t=40, b=20))

SAMPLE_CSV = Path(__file__).parent / "sample_orders.csv"

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    default_base_url: str
    chat_base_url_suffix: str
    probe: Callable[..., list[str]]
    needs_api_key: bool
    notes: str


def _probe_openai_models(api_url: str, api_key: str = "") -> list[str]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    r = requests.get(f"{api_url.rstrip('/')}/models", timeout=5, headers=headers)
    r.raise_for_status()
    payload = r.json()
    items = payload.get("data") or payload.get("models") or []
    ids = [
        (it if isinstance(it, str) else it.get("id") or it.get("name"))
        for it in items
        if isinstance(it, str) or isinstance(it, dict)
    ]
    return sorted(x for x in ids if x)


def probe_llamacpp(base_url: str, api_key: str = "") -> list[str]:
    return _probe_openai_models(f"{base_url.rstrip('/')}/v1")


def probe_ollama(base_url: str, api_key: str = "") -> list[str]:
    r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=2)
    r.raise_for_status()
    return sorted(m["name"] for m in r.json().get("models", []) if m.get("name"))


def probe_docker(base_url: str, api_key: str = "") -> list[str]:
    return _probe_openai_models(f"{base_url.rstrip('/')}/engines/v1")


def probe_remote(base_url: str, api_key: str = "") -> list[str]:
    return _probe_openai_models(base_url, api_key)


PROVIDERS: dict[str, Provider] = {
    "llamacpp": Provider(
        key="llamacpp",
        label="llama.cpp (local)",
        default_base_url="http://localhost:8080",
        chat_base_url_suffix="/v1",
        probe=probe_llamacpp,
        needs_api_key=False,
        notes="Default `pixi run serve` port for the llamacpp capability is 8080.",
    ),
    "ollama": Provider(
        key="ollama",
        label="Ollama (local)",
        default_base_url="http://localhost:11434",
        chat_base_url_suffix="/v1",
        probe=probe_ollama,
        needs_api_key=False,
        notes="Start with `ollama serve`; the desktop app starts it automatically.",
    ),
    "docker": Provider(
        key="docker",
        label="Docker Model Runner (local)",
        default_base_url="http://localhost:12434",
        chat_base_url_suffix="/engines/v1",
        probe=probe_docker,
        needs_api_key=False,
        notes="Enable Model Runner in Docker Desktop and pull a model with `docker model pull`.",
    ),
    "remote": Provider(
        key="remote",
        label="Remote (OpenAI-compatible)",
        default_base_url="https://api.openai.com/v1",
        chat_base_url_suffix="",
        probe=probe_remote,
        needs_api_key=True,
        notes="Any OpenAI-compatible API. Examples: api.openai.com/v1, api.together.xyz/v1, api.groq.com/openai/v1.",
    ),
}

# ---------------------------------------------------------------------------
# Data helpers (all cached)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Parsing CSV…")
def _load_csv(data: bytes) -> pd.DataFrame:
    """Parse CSV bytes. Cached so re-uploading the same file is instant."""
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception:
        df = pd.read_csv(io.BytesIO(data), sep=None, engine="python")
    return _sanitize_df(df)


@st.cache_data(show_spinner=False)
def _sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Period columns to strings so Plotly can JSON-serialize them."""
    out = df.copy()
    for col in out.columns:
        if isinstance(out[col].dtype, pd.PeriodDtype):
            out[col] = out[col].astype(str)
        elif hasattr(out[col], "cat") and isinstance(
            getattr(out[col].cat, "categories", pd.Index([])).dtype, pd.PeriodDtype
        ):
            out[col] = out[col].astype(str)
    return out


@st.cache_data(show_spinner=False)
def _get_col_types(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    """Return (numeric, categorical, date) column name lists."""
    return (
        df.select_dtypes(include="number").columns.tolist(),
        df.select_dtypes(include=["object", "category", "bool"]).columns.tolist(),
        df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist(),
    )


@st.cache_data(show_spinner=False)
def _schema_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build a schema summary table. Cached to avoid O(n) work on every rerun."""
    return pd.DataFrame({
        "column":   df.columns,
        "dtype":    [str(t) for t in df.dtypes],
        "non_null": df.notna().sum().values,
        "n_unique": [df[c].nunique(dropna=True) for c in df.columns],
    })


def _sanitize_value(obj: object) -> object:
    """Recursively replace pd.Period objects with strings.

    Even when the source DataFrame is sanitized, LLM-generated code can create
    new Period objects (via to_period(), resample(), etc.). Walking the figure
    dict before Plotly's JSON encoder sees it is the only reliable guard.
    """
    if isinstance(obj, pd.Period):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_value(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        cleaned = [_sanitize_value(v) for v in obj]
        return type(obj)(cleaned)
    return obj


@st.cache_data(show_spinner=False)
def _exec_chart_cached(code: str, df: pd.DataFrame) -> go.Figure | str:
    """Execute AI-generated Plotly code and return the figure. Cached for instant history replay."""
    namespace = {"df": _sanitize_df(df), "pd": pd, "px": px, "go": go}
    try:
        exec(code, namespace)  # noqa: S102
    except Exception as exc:
        return f"Code execution error: {exc}"
    fig = namespace.get("fig")
    if not isinstance(fig, go.Figure):
        return "The generated code did not produce a valid Plotly figure (`fig` not assigned)."
    fig = go.Figure(_sanitize_value(fig.to_dict()))
    fig.update_layout(**_CHART_MARGIN)
    return fig


# ---------------------------------------------------------------------------
# Chart Builder
# ---------------------------------------------------------------------------
# @st.fragment isolates widget reruns: changing any control only reruns this
# function, not the entire page, making chart updates feel instant.


@st.fragment
def _render_chart_builder(df: pd.DataFrame) -> None:
    num, cat, date = _get_col_types(df)
    ctrl_col, chart_col = st.columns([1, 3], gap="large")
    fig: go.Figure | None = None

    with ctrl_col:
        chart_type = st.selectbox(
            "Chart type",
            options=[k for k, _ in CHART_TYPES],
            format_func=CHART_TYPE_LABELS.__getitem__,
            key="chart_type",
        )

        if chart_type == "heatmap":
            if len(num) < 2:
                st.warning("Need at least 2 numeric columns for a correlation heatmap.")
            else:
                selected = st.multiselect("Columns", options=num, default=num, key="heatmap_cols")
                if selected:
                    fig = px.imshow(
                        df[selected].corr(),
                        text_auto=".2f",
                        color_continuous_scale="RdBu_r",
                        zmin=-1, zmax=1,
                        title="Correlation Matrix",
                    )

        elif chart_type == "histogram":
            if not num:
                st.warning("No numeric columns available.")
            else:
                x_col = st.selectbox("Column", options=num, key="hist_x")
                color_col = st.selectbox("Color by", options=["(none)"] + cat, key="hist_color")
                nbins = st.slider("Bins", min_value=5, max_value=100, value=20, key="hist_bins")
                kwargs = dict(x=x_col, nbins=nbins, title=f"Distribution of {x_col}")
                if color_col != "(none)":
                    kwargs.update(color=color_col, barmode="overlay", opacity=0.7)
                fig = px.histogram(df, **kwargs)

        elif chart_type == "pie":
            if not cat or not num:
                st.warning("Need at least one categorical and one numeric column.")
            else:
                names_col = st.selectbox("Labels (categorical)", options=cat, key="pie_names")
                values_col = st.selectbox("Values (numeric)", options=num, key="pie_values")
                agg_df = df.groupby(names_col)[values_col].sum().reset_index()
                fig = px.pie(agg_df, names=names_col, values=values_col, title=f"{values_col} by {names_col}")

        elif chart_type == "scatter":
            if len(num) < 2:
                st.warning("Need at least 2 numeric columns for a scatter plot.")
            else:
                x_col = st.selectbox("X axis", options=num, key="scatter_x")
                y_options = [c for c in num if c != x_col] or num
                y_col = st.selectbox("Y axis", options=y_options, key="scatter_y")
                color_col = st.selectbox("Color by", options=["(none)"] + cat + num, key="scatter_color")
                size_col = st.selectbox("Size by", options=["(none)"] + num, key="scatter_size")
                kwargs = dict(x=x_col, y=y_col, title=f"{y_col} vs {x_col}", hover_data=df.columns.tolist())
                if color_col != "(none)":
                    kwargs["color"] = color_col
                if size_col != "(none)":
                    kwargs.update(size=size_col, size_max=20)
                fig = px.scatter(df, **kwargs)

        elif chart_type == "box":
            if not num:
                st.warning("No numeric columns available.")
            else:
                y_col = st.selectbox("Y axis (numeric)", options=num, key="box_y")
                x_col = st.selectbox("X axis (group by)", options=["(none)"] + cat, key="box_x")
                color_col = st.selectbox("Color by", options=["(none)"] + cat, key="box_color")
                kwargs = dict(y=y_col, title=f"Distribution of {y_col}")
                if x_col != "(none)":
                    kwargs["x"] = x_col
                if color_col != "(none)":
                    kwargs["color"] = color_col
                fig = px.box(df, **kwargs)

        else:  # bar, line, area
            if not num:
                st.warning("No numeric columns available.")
            else:
                x_col = st.selectbox("X axis", options=cat + date + num, key=f"{chart_type}_x")
                y_col = st.selectbox("Y axis (numeric)", options=num, key=f"{chart_type}_y")
                color_col = st.selectbox("Color / group by", options=["(none)"] + cat, key=f"{chart_type}_color")
                group_cols = [x_col] + ([color_col] if color_col != "(none)" else [])

                if chart_type == "bar":
                    agg_func = st.selectbox("Aggregation", options=AGG_FUNCS, key="bar_agg")
                    barmode = st.selectbox("Bar mode", options=["group", "stack", "relative"], key="bar_mode")
                    plot_df = df.groupby(group_cols)[y_col].agg(agg_func).reset_index()
                    kwargs = dict(x=x_col, y=y_col, title=f"{agg_func.title()} of {y_col} by {x_col}", barmode=barmode)
                    if color_col != "(none)":
                        kwargs["color"] = color_col
                    fig = px.bar(plot_df, **kwargs)

                elif chart_type == "line":
                    kwargs = dict(x=x_col, y=y_col, title=f"{y_col} over {x_col}", markers=True)
                    if color_col != "(none)":
                        kwargs["color"] = color_col
                    fig = px.line(df.sort_values(x_col), **kwargs)

                elif chart_type == "area":
                    kwargs = dict(x=x_col, y=y_col, title=f"{y_col} over {x_col}")
                    if color_col != "(none)":
                        kwargs["color"] = color_col
                    fig = px.area(df.sort_values(x_col), **kwargs)

    with chart_col:
        if fig is not None:
            fig.update_layout(**_CHART_MARGIN)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Configure the chart options on the left.")


# ---------------------------------------------------------------------------
# AI Chart
# ---------------------------------------------------------------------------

_AI_SYSTEM = textwrap.dedent("""
    You are a data visualization assistant. The user has a pandas DataFrame called `df`.

    Always respond in this exact format:
    1. One to two sentences in plain English describing what the chart will show and any key insight.
    2. A single fenced ```python code block with the Plotly figure code.

    Rules for the code block:
    - Assign the final figure to a variable called `fig`.
    - Do not import any libraries — `pd`, `px` (plotly.express), and `go` (plotly.graph_objects) are already in scope.
    - Do not call `fig.show()` or `st.plotly_chart()`.
    - Do not read any files; `df` is already loaded.
    - Keep the code concise and correct.

    If the request is impossible (e.g. a column doesn't exist), explain why in plain text and omit the code block.
""").strip()


def _extract_code(text: str) -> str | None:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else None


def _description_stream(stream, collected: list[str]) -> Generator[str, None, None]:
    """Yield only the plain-English description that precedes the first code fence.

    All tokens are appended to `collected` so the caller can reconstruct the
    full response after the generator is exhausted. Code-block tokens are
    consumed silently so they never appear in the streamed chat bubble.
    """
    pending = ""
    code_started = False
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta is None:
            continue
        collected.append(delta)
        if code_started:
            continue
        pending += delta
        fence = pending.find("```")
        if fence != -1:
            before = pending[:fence].rstrip()
            if before:
                yield before
            code_started = True
        else:
            # Hold back 3 chars to avoid splitting ``` across chunk boundaries.
            if len(pending) > 3:
                yield pending[:-3]
                pending = pending[-3:]
    if not code_started and pending:
        yield pending


def _render_chart_result(code: str, df: pd.DataFrame) -> None:
    """Execute `code`, render the resulting figure, and show the code expander."""
    result = _exec_chart_cached(code, df)
    if isinstance(result, go.Figure):
        st.plotly_chart(result, use_container_width=True)
    else:
        st.error(result)
    with st.expander("Generated code"):
        st.code(code, language="python")


def _render_ai_chart(
    df: pd.DataFrame,
    provider: Provider,
    base_url: str,
    api_key: str,
    model: str,
    available: list[str],
) -> None:
    ss = st.session_state
    chat_container = st.container(height=520)

    with chat_container:
        for entry in ss.ai_messages:
            with st.chat_message(entry["role"]):
                # Show description for assistant messages (not the raw text which
                # contains the code block); fall back to text for legacy entries.
                st.markdown(entry.get("description") or entry.get("text", ""))
                if entry.get("code"):
                    _render_chart_result(entry["code"], df)

    prompt = st.chat_input("Describe a chart… e.g. 'show total revenue by region as a bar chart'")
    if not prompt:
        return

    if not available:
        st.warning("Pick a provider and scan for a model first in **Settings**.")
        return

    schema_text = "\n".join(f"- {c}: {df[c].dtype}" for c in df.columns)
    user_context = (
        f"DataFrame schema:\n{schema_text}\n\n"
        f"First 10 rows (CSV):\n{df.head(10).to_csv(index=False)}\n\n"
        f"Request: {prompt}"
    )

    ss.ai_messages.append({"role": "user", "text": prompt, "code": None})

    llm_messages = (
        [{"role": "system", "content": _AI_SYSTEM}]
        + [{"role": m["role"], "content": m["text"]} for m in ss.ai_messages]
    )
    llm_messages[-1]["content"] = user_context

    client = OpenAI(
        base_url=f"{base_url.rstrip('/')}{provider.chat_base_url_suffix}",
        api_key=api_key if (provider.needs_api_key and api_key) else "not-needed",
    )
    collected: list[str] = []

    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                stream = client.chat.completions.create(
                    model=model, messages=llm_messages, stream=True,
                )
                # Stream only the plain-English description; code tokens are
                # buffered in `collected` and extracted after streaming completes.
                description = st.write_stream(_description_stream(stream, collected))
            except Exception as exc:
                err = f"**Error talking to {provider.label}:** {exc}"
                st.markdown(err)
                ss.ai_messages.append({"role": "assistant", "text": err, "description": err, "code": None})
                return

            full_text = "".join(collected)
            code = _extract_code(full_text)
            if code:
                _render_chart_result(code, df)

    ss.ai_messages.append({
        "role": "assistant",
        "text": full_text,           # full response kept for LLM conversation history
        "description": description,  # description-only shown in chat replay
        "code": code,
    })


# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Data Visualizer", layout="wide")

ss = st.session_state
ss.setdefault("df", None)
ss.setdefault("filename", None)
ss.setdefault("models_for_provider", {})
ss.setdefault("ai_messages", [])


def _set_dataframe(df: pd.DataFrame, name: str) -> None:
    """Store a newly loaded DataFrame and trigger a clean rerun."""
    ss.df = df
    ss.filename = name
    ss.ai_messages = []
    st.toast(f"Loaded {name} — {len(df):,} rows × {len(df.columns)} cols")
    st.rerun()


with st.expander("Settings", expanded=ss.df is None):
    model_col, data_col = st.columns(2, gap="large")

    with model_col:
        st.markdown("**Model** *(used by the AI Chart tab)*")
        provider_key = st.selectbox(
            "Provider",
            options=list(PROVIDERS.keys()),
            format_func=lambda k: PROVIDERS[k].label,
            key="provider_key",
        )
        provider = PROVIDERS[provider_key]
        base_url = st.text_input(
            "Base URL", value=provider.default_base_url, key=f"base_{provider_key}"
        )
        api_key = ""
        if provider.needs_api_key:
            api_key = st.text_input("API key", value="", type="password", key=f"key_{provider_key}")
        st.caption(provider.notes)
        if provider.needs_api_key:
            st.warning(
                "⚠ Using a remote provider sends your data (schema and a 10-row sample) "
                "off this device to a third-party API."
            )

        if st.button("Scan for running models", use_container_width=True):
            try:
                models = provider.probe(base_url, api_key)
                ss.models_for_provider[provider_key] = models
                if models:
                    st.success(f"Found {len(models)} model(s).")
                else:
                    st.warning("Provider responded but reported no loaded models.")
            except requests.exceptions.ConnectionError:
                st.error(f"Could not reach {base_url}. Is the provider running?")
            except Exception as exc:
                st.error(f"Scan failed: {exc}")

        available = ss.models_for_provider.get(provider_key, [])
        model = st.selectbox(
            "Model",
            options=available or ["— scan to populate —"],
            disabled=not available,
            key=f"model_{provider_key}",
        )

    with data_col:
        st.markdown("**Data**")
        upload = st.file_uploader("Upload CSV", type=["csv"], accept_multiple_files=False)
        if upload is not None and upload.name != ss.filename:
            try:
                _set_dataframe(_load_csv(upload.read()), upload.name)
            except Exception as exc:
                st.error(f"Could not parse CSV: {exc}")

        if SAMPLE_CSV.exists() and st.button(
            "Load sample data",
            use_container_width=True,
            help=f"Load bundled {SAMPLE_CSV.name} — synthetic orders dataset for trying the app.",
        ):
            _set_dataframe(_load_csv(SAMPLE_CSV.read_bytes()), SAMPLE_CSV.name)

# ---------------------------------------------------------------------------
# Main content — only shown once data is loaded
# ---------------------------------------------------------------------------

df: pd.DataFrame | None = ss.df

if df is None:
    st.info(
        "Upload a CSV in **Settings** above — or click **Load sample data** "
        "to try with a synthetic orders dataset."
    )
    st.stop()

st.subheader(ss.filename)
st.caption(f"{len(df):,} rows × {len(df.columns)} columns")

builder_tab, ai_tab, data_tab = st.tabs(["Chart Builder", "AI Chart", "Data"])

with builder_tab:
    _render_chart_builder(df)

with ai_tab:
    _render_ai_chart(df, provider, base_url, api_key, model, available)

with data_tab:
    st.dataframe(df, use_container_width=True, height=500)
    with st.expander("Schema"):
        st.dataframe(_schema_table(df), use_container_width=True, hide_index=True)
