"""Data Explorer — upload a CSV, view it as a table, chat with it via an LLM.

Supports three local OpenAI-compatible servers (llama.cpp, Ollama, Docker
Model Runner) plus a generic remote OpenAI-compatible provider for hosted
APIs like OpenAI, Together, or Groq.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import requests
import streamlit as st
from openai import OpenAI

# ---------------------------------------------------------------------------
# Provider registry
#
# Every supported runtime exposes an OpenAI-compatible /v1/chat/completions,
# but they differ in (a) default port and (b) how to enumerate the models
# that are actually loaded right now. The probe function returns a list of
# model identifiers the user can pick from.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    default_base_url: str
    chat_base_url_suffix: str  # Appended to base_url for the OpenAI client base_url
    probe: Callable[..., list[str]]
    needs_api_key: bool
    notes: str


def _probe_openai_models(api_url: str, api_key: str = "") -> list[str]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    r = requests.get(f"{api_url.rstrip('/')}/models", timeout=5, headers=headers)
    r.raise_for_status()
    payload = r.json()
    items = payload.get("data") or payload.get("models") or []
    out: list[str] = []
    for it in items:
        if isinstance(it, str):
            out.append(it)
        elif isinstance(it, dict):
            mid = it.get("id") or it.get("name")
            if mid:
                out.append(mid)
    return sorted(out)


def probe_llamacpp(base_url: str, api_key: str = "") -> list[str]:
    # llama.cpp serves /v1/models even when only one model is loaded.
    return _probe_openai_models(f"{base_url.rstrip('/')}/v1")


def probe_ollama(base_url: str, api_key: str = "") -> list[str]:
    # Ollama's native API exposes locally-pulled models at /api/tags.
    r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=2)
    r.raise_for_status()
    return sorted(m["name"] for m in r.json().get("models", []) if m.get("name"))


def probe_docker(base_url: str, api_key: str = "") -> list[str]:
    # Docker Model Runner exposes OpenAI under /engines/v1.
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
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Data Explorer", layout="wide")

# Persisted UI state
ss = st.session_state
ss.setdefault("df", None)
ss.setdefault("filename", None)
ss.setdefault("messages", [])  # chat history shown to user
ss.setdefault("models_for_provider", {})  # provider_key -> list[str]


SAMPLE_CSV = Path(__file__).parent / "sample_orders.csv"


def _load_csv(uploaded) -> pd.DataFrame:
    # Read once into bytes so we can retry with different separators if needed.
    raw = uploaded.read()
    try:
        return pd.read_csv(io.BytesIO(raw))
    except Exception:
        return pd.read_csv(io.BytesIO(raw), sep=None, engine="python")


# --- Settings: model + data selection (in-page, no sidebar) ---------------
# Collapse the Settings panel as soon as a dataset is loaded (upload or
# sample) so the chat area becomes the natural focus. The chat input still
# warns if a model hasn't been picked yet.
with st.expander("Settings", expanded=ss.df is None):
    model_col, data_col = st.columns(2, gap="large")

    with model_col:
        st.markdown("**Model**")
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
            api_key = st.text_input(
                "API key", value="", type="password", key=f"key_{provider_key}"
            )
        st.caption(provider.notes)
        if provider.needs_api_key:
            st.warning(
                "⚠ Using a remote provider sends your data (including the CSV "
                "sample and summary statistics) off this device to a third-party API."
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
            except Exception as e:
                st.error(f"Scan failed: {e}")

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
                ss.df = _load_csv(upload)
                ss.filename = upload.name
                ss.messages = []
                st.toast(f"Loaded {upload.name} — {len(ss.df):,} rows × {len(ss.df.columns)} cols")
                # Re-run so the expander re-renders with ss.df set and collapses.
                st.rerun()
            except Exception as e:
                st.error(f"Could not parse CSV: {e}")

        if SAMPLE_CSV.exists() and st.button(
            "Load sample data",
            use_container_width=True,
            help=f"Load bundled {SAMPLE_CSV.name} — synthetic orders dataset for trying the app.",
        ):
            ss.df = pd.read_csv(SAMPLE_CSV)
            ss.filename = SAMPLE_CSV.name
            ss.messages = []
            st.toast(f"Loaded {SAMPLE_CSV.name} — {len(ss.df):,} rows × {len(ss.df.columns)} cols")
            # Re-run so the expander re-renders with ss.df set and collapses.
            st.rerun()

# --- Main: data table + chat ----------------------------------------------
df: pd.DataFrame | None = ss.df

if df is None:
    st.info("Upload a CSV in **Settings** above — or click **Load sample data** to try it with a synthetic orders dataset.")
    st.stop()

data_col, chat_col = st.columns([2, 1], gap="large")

with data_col:
    st.subheader(ss.filename)
    st.caption(f"{len(df):,} rows × {len(df.columns)} columns")
    st.dataframe(df, use_container_width=True, height=480)
    with st.expander("Schema"):
        schema = pd.DataFrame({
            "column": df.columns,
            "dtype": [str(t) for t in df.dtypes],
            "non_null": df.notna().sum().values,
            "n_unique": [df[c].nunique(dropna=True) for c in df.columns],
        })
        st.dataframe(schema, use_container_width=True, hide_index=True)

with chat_col:
    st.subheader("Chat with the data")
    chat_container = st.container(height=480)
    with chat_container:
        for msg in ss.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # chat_input rendered inside a column (not at top level) is inline rather
    # than bottom-pinned, which sits it just below chat_container.
    prompt = st.chat_input("Ask a question about the data…")
if prompt:
    if not available:
        st.warning("Pick a provider and scan for a model first.")
        st.stop()

    ss.messages.append({"role": "user", "content": prompt})

    head_sample = df.head(20).to_csv(index=False)
    try:
        describe = df.describe(include="all").to_csv()
    except Exception as e:
        describe = f"(describe failed: {e})"
    schema_text = "\n".join(f"- {c}: {df[c].dtype}" for c in df.columns)
    system = (
        "You are a data analyst helping the user understand a pandas DataFrame named `df`. "
        f"It has {len(df):,} rows and {len(df.columns)} columns.\n\n"
        f"Schema:\n{schema_text}\n\n"
        f"First 20 rows (CSV):\n{head_sample}\n"
        f"Summary statistics (CSV):\n{describe}\n"
        "Answer questions about this data. When useful, show the pandas snippet you would run, "
        "but compute final answers yourself from the sample and stats above. If a question requires "
        "the full dataset and the sample is insufficient, say so explicitly."
    )
    client = OpenAI(
        base_url=f"{base_url.rstrip('/')}{provider.chat_base_url_suffix}",
        api_key=api_key if (provider.needs_api_key and api_key) else "not-needed",
    )
    llm_messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in ss.messages
    ]

    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            collected = []
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=llm_messages,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        collected.append(delta)
                        placeholder.markdown("".join(collected))
                reply = "".join(collected) or "(empty response)"
            except Exception as e:
                reply = f"**Error talking to {provider.label}:** {e}"
                placeholder.markdown(reply)

    ss.messages.append({"role": "assistant", "content": reply})
