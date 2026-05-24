import streamlit as st
from agent import run_agent

st.set_page_config(
    page_title="Research Agent",
    page_icon="🔍",
    layout="wide"
)

st.title("Autonomous Research Agent")
st.caption("Multi-agent system: Planner → Searcher → Critic → Writer")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("How it works")
    st.markdown("""
**Planner** breaks your topic into search queries

**Searcher** hits the web 3–5 times across different angles

**Critic** scores coverage 1–10 and loops back if score < 7

**Writer** synthesises everything into a cited report
    """)
    st.divider()
    st.caption("Built with Claude + Tavily + Streamlit")

# ── Main input ────────────────────────────────────────────────────────────────
topic = st.text_input(
    "Research topic",
    placeholder="e.g. Impact of AI on software engineering jobs in 2025",
    label_visibility="visible"
)

col1, col2 = st.columns([1, 5])
with col1:
    run_btn = st.button("Research", type="primary", use_container_width=True)

# ── Agent run ─────────────────────────────────────────────────────────────────
if run_btn and topic.strip():
    st.divider()

    # Live agent log
    log_header = st.subheader("Agent reasoning")
    log_area = st.container()
    log_messages = []

    ICONS = {
        "planner": "🧠",
        "search":  "🔍",
        "critic":  "⚖️",
        "writer":  "✍️",
    }

    log_placeholder = log_area.empty()

    def on_update(stage, message):
        icon = ICONS.get(stage, "•")
        log_messages.append(f"{icon} **{stage.capitalize()}** — {message}")
        log_placeholder.markdown("\n\n".join(log_messages))

    with st.spinner("Agent working..."):
        report, sources = run_agent(topic.strip(), on_update=on_update)

    st.divider()

    # Report output
    st.subheader("Research report")

    tab1, tab2 = st.tabs(["Rendered", "Raw markdown"])

    with tab1:
        st.markdown(report)

    with tab2:
        st.code(report, language="markdown")

    # Sources
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for i, url in enumerate(sources, 1):
                st.markdown(f"{i}. {url}")

    # Download
    st.download_button(
        label="Download report (.md)",
        data=report,
        file_name=f"research_{topic[:30].replace(' ','_')}.md",
        mime="text/markdown"
    )

elif run_btn and not topic.strip():
    st.warning("Please enter a research topic first.")