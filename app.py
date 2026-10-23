"""
app.py
------
The Streamlit dashboard: sidebar, eight pages and all the styling.

Analogy: The front desk — it takes your request, asks the specialist
files for answers, and draws the results.

Pages
-----
Dashboard · Segments · Storage · Network · Availability · Probability ·
Integrity · Export

Run with:
    streamlit run app.py
"""

import copy

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from assignment import AssignmentEngine
from availability import AvailabilitySimulator
from blockchain import Blockchain
from export import ExportEngine
from integrity import IntegrityChecker
from probability import (
    calculate_multiple_curves,
    calculate_probability_curve,
    exact_segment_loss_probability,
    get_assumptions_explanation,
    segment_loss_probability,
)
from segmentation import SegmentationEngine
from storage_metrics import StorageMetrics

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="SegmentChain Simulator",
    page_icon="⛓️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS theme injection
# ---------------------------------------------------------------------------

def inject_css() -> None:
    st.markdown(
        """
        <style>
        /* ── Google Fonts ── */
        @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=JetBrains+Mono:wght@400;500&family=Public+Sans:wght@400;500;600&display=swap');

        :root {
            --accent: #0B6E6E;
            --accent-light: #4FD1C5;
            --s1: #0B6E6E; --s2: #B4540A; --s3: #6D3FC4; --s4: #B4235A; --s5: #2559C9;
        }

        html, body, [class*="css"] {
            font-family: 'Public Sans', 'Segoe UI', sans-serif;
        }

        h1, h2, h3 {
            font-family: 'Bricolage Grotesque', 'Segoe UI', sans-serif !important;
        }

        code, pre, .stCode {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Metric cards */
        [data-testid="metric-container"] {
            background: rgba(11, 110, 110, 0.06);
            border: 1px solid rgba(11, 110, 110, 0.2);
            border-radius: 12px;
            padding: 1rem;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(160deg, #0B131B 0%, #0f2020 100%);
        }
        [data-testid="stSidebar"] * {
            color: #E7EEF4 !important;
        }
        [data-testid="stSidebar"] .stSlider > label {
            color: #93A4B4 !important;
        }

        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #0B6E6E, #0D8F8F);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #0D8F8F, #0B6E6E);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(11,110,110,0.3);
        }

        /* Section headers */
        .sc-eyebrow {
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #52616F;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        /* Info blocks */
        .sc-note {
            border-left: 3px solid #0B6E6E;
            background: rgba(11, 110, 110, 0.06);
            padding: 0.7rem 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.5rem 0;
            font-size: 0.93rem;
        }

        /* Segment colour pills */
        .seg-pill {
            display: inline-block;
            padding: 0.15rem 0.6rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            margin: 0.1rem;
            color: white;
        }
        .s1 { background: #0B6E6E; }
        .s2 { background: #B4540A; }
        .s3 { background: #6D3FC4; }
        .s4 { background: #B4235A; }
        .s5 { background: #2559C9; }

        /* Tables */
        .stDataFrame { border-radius: 8px; overflow: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def initialize_session_state() -> None:
    defaults = {
        "simulated": False,
        "blockchain": None,
        "segmentation_engine": None,
        "assignment_engine": None,
        "storage_metrics": None,
        "availability_sim": None,
        "integrity_checker": None,
        "export_engine": ExportEngine(output_dir="."),
        "config": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def run_simulation(
    num_blocks: int,
    tx_per_block: int,
    seed: int,
    num_segments: int,
    num_nodes: int,
    replicas: int,
    header_size: int,
    state_size: int,
    block_data_size: int,
) -> None:
    """
    The six steps described in Part 4 of the Deep Dive:

    1. Read the sidebar (done by the caller; params passed in here).
    2. Build the chain.
    3. Cut into segments.
    4. Place replicas.
    5. Prepare availability and integrity tools.
    6. Compute storage.
    """
    with st.spinner("Building chain…"):
        bc = Blockchain.generate_chain(num_blocks, tx_per_block, seed)

    with st.spinner("Partitioning segments…"):
        se = SegmentationEngine()
        se.partition_segments(bc.blocks, num_segments)

    with st.spinner("Assigning replicas…"):
        ae = AssignmentEngine()
        ae.assign_segment_replicas(se.segments, num_nodes, replicas, seed)

    with st.spinner("Preparing tools…"):
        avail_sim = AvailabilitySimulator(ae)
        integrity = IntegrityChecker(bc)

    with st.spinner("Computing storage…"):
        sm = StorageMetrics(block_data_size, header_size, state_size)
        sm.calculate_segmented_storage(ae, se, num_blocks)

    st.session_state.update(
        simulated=True,
        blockchain=bc,
        segmentation_engine=se,
        assignment_engine=ae,
        storage_metrics=sm,
        availability_sim=avail_sim,
        integrity_checker=integrity,
        config={
            "num_blocks": num_blocks,
            "tx_per_block": tx_per_block,
            "seed": seed,
            "num_segments": num_segments,
            "num_nodes": num_nodes,
            "replicas": replicas,
            "header_size": header_size,
            "state_size": state_size,
            "block_data_size": block_data_size,
        },
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def sidebar() -> None:
    st.sidebar.markdown("## ⛓️ SegmentChain")
    st.sidebar.markdown("*Segment blockchain simulator*")
    st.sidebar.divider()

    st.sidebar.markdown("### Chain")
    num_blocks   = st.sidebar.slider("Blocks",              10, 1000, 100, 10)
    tx_per_block = st.sidebar.slider("Transactions / block", 1,  100,   5)
    seed         = st.sidebar.slider("Random seed",          0, 10000,  7)

    st.sidebar.markdown("### Network")
    num_segments = st.sidebar.slider("Segments",              2,  50,  5)
    num_nodes    = st.sidebar.slider("Nodes",                 3, 100, 30)
    replicas     = st.sidebar.slider("Replicas per segment",  1,  10,  3)

    st.sidebar.markdown("### Storage model (bytes)")
    header_size     = st.sidebar.slider("Header size",    32,   512,  160)
    state_size      = st.sidebar.slider("State size",   1024, 16384, 4096, 1024)
    block_data_size = st.sidebar.slider("Block data",    100, 10000, 1000, 100)

    st.sidebar.divider()
    if st.sidebar.button("🚀 Generate Simulation", use_container_width=True):
        run_simulation(
            num_blocks, tx_per_block, seed,
            num_segments, num_nodes, replicas,
            header_size, state_size, block_data_size,
        )
        st.rerun()

    if st.session_state.simulated:
        st.sidebar.success("✅ Simulation ready")
        cfg = st.session_state.config
        st.sidebar.caption(
            f"{cfg['num_blocks']} blocks · {cfg['num_segments']} segments · "
            f"{cfg['num_nodes']} nodes · {cfg['replicas']} replicas · seed {cfg['seed']}"
        )


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

SEG_COLORS = {
    "S1": "#0B6E6E", "S2": "#B4540A", "S3": "#6D3FC4",
    "S4": "#B4235A", "S5": "#2559C9",
}

def seg_color(seg_id: str) -> str:
    idx = int(seg_id[1:]) if len(seg_id) > 1 and seg_id[1:].isdigit() else 0
    palette = ["#0B6E6E", "#B4540A", "#6D3FC4", "#B4235A", "#2559C9",
               "#1a7a5e", "#8b5523", "#5a3494", "#9c1e4a", "#1e48a8"]
    return palette[(idx - 1) % len(palette)]

def style_fig(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Public Sans, Segoe UI, sans-serif", size=13),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(100,100,100,0.15)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(100,100,100,0.15)")
    return fig

def stat_card(label: str, value: str, delta: str = "") -> None:
    st.metric(label=label, value=value, delta=delta or None)


# ---------------------------------------------------------------------------
# ── PAGE: Dashboard ──────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def page_dashboard() -> None:
    st.title("⛓️ SegmentChain Dashboard")
    if not st.session_state.simulated:
        st.info("👈 Configure parameters in the sidebar and press **Generate Simulation**.")
        _show_concept_intro()
        return

    bc  = st.session_state.blockchain
    sm  = st.session_state.storage_metrics
    se  = st.session_state.segmentation_engine
    ae  = st.session_state.assignment_engine
    cfg = st.session_state.config

    info = bc.get_chain_info()

    # ── Key numbers ────────────────────────────────────────────────────
    st.markdown("### Key numbers")
    c1, c2, c3, c4 = st.columns(4)
    with c1: stat_card("Blocks", str(info["total_blocks"]))
    with c2: stat_card("Transactions", f"{info['total_transactions']:,}")
    with c3: stat_card("Segments", str(len(se.segments)))
    with c4: stat_card("Nodes", str(len(ae.nodes)))

    c1, c2, c3 = st.columns(3)
    with c1: stat_card("Full-node storage", StorageMetrics.format_bytes(sm.full_node_bytes))
    with c2: stat_card("Avg segmented node", StorageMetrics.format_bytes(sm.average_node_bytes))
    with c3: stat_card("Storage saving", f"{sm.reduction_percentage:.1f}%")

    # ── Storage breakdown bar ───────────────────────────────────────────
    st.markdown("### Storage comparison")
    full = sm.full_node_bytes
    avg  = sm.average_node_bytes
    hdr  = cfg["num_blocks"] * cfg["header_size"]
    st8  = cfg["state_size"]
    full_data = full - hdr - st8
    avg_data  = max(0, avg - hdr - st8)

    fig = go.Figure()
    for label, data, h, s in [
        ("Full node", full_data, hdr, st8),
        ("Segmented (avg)", avg_data, hdr, st8),
    ]:
        fig.add_bar(name="Block data", x=[label], y=[data], marker_color="#0B6E6E", showlegend=label == "Full node")
        fig.add_bar(name="Headers",    x=[label], y=[h],    marker_color="#6D3FC4", showlegend=label == "Full node")
        fig.add_bar(name="State",      x=[label], y=[s],    marker_color="#B4540A", showlegend=label == "Full node")

    fig.update_layout(barmode="stack", yaxis_title="Bytes")
    st.plotly_chart(style_fig(fig), use_container_width=True)

    # ── Genesis and latest blocks ───────────────────────────────────────
    st.markdown("### Chain sample")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Genesis block (index 0)**")
        g = bc.blocks[0]
        st.json(g.to_dict(), expanded=False)
    with col2:
        st.markdown(f"**Latest block (index {len(bc)-1})**")
        latest = bc.blocks[-1]
        st.json(latest.to_dict(), expanded=False)


def _show_concept_intro():
    st.markdown("---")
    st.markdown("## What is SegmentChain?")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**Normal blockchain**: Every node stores all block data, all headers and the
current state. Safe, but each node holds the whole history.

**Segment blockchain**: History is cut into segments. A node stores block data
for only its segments, plus every header and the state.  Each segment is
copied onto *m* nodes.
        """)
    with col2:
        st.markdown("""
**Five ideas to start:**

1. A blockchain is a list of records linked by fingerprints.
2. Change an old record and every fingerprint after it breaks.
3. Many computers (nodes) keep copies.
4. SegmentChain: each node keeps only a few segments.
5. This app is a *simulator* that measures the storage saved.
        """)


# ---------------------------------------------------------------------------
# ── PAGE: Segments ───────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def page_segments() -> None:
    st.title("🔪 Segments")
    if not st.session_state.simulated:
        st.info("Run the simulation first.")
        return

    se  = st.session_state.segmentation_engine
    ae  = st.session_state.assignment_engine
    cfg = st.session_state.config

    st.markdown("### Segment partition")
    st.caption(
        f"{cfg['num_blocks']} blocks split into {len(se.segments)} segments of "
        f"~{cfg['num_blocks'] // len(se.segments)} blocks each."
    )

    rows = []
    for seg in se.segments:
        holders = ae.segment_replicas.get(seg.segment_id, [])
        rows.append({
            "Segment": seg.segment_id,
            "Start block": seg.start_height,
            "End block":   seg.end_height,
            "Block count": seg.block_count,
            "Stored on":   ", ".join(holders),
            "Replicas":    len(holders),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Block-count bar
    st.markdown("### Blocks per segment")
    fig = go.Figure(go.Bar(
        x=[r["Segment"] for r in rows],
        y=[r["Block count"] for r in rows],
        marker_color=[seg_color(r["Segment"]) for r in rows],
        text=[r["Block count"] for r in rows],
        textposition="outside",
    ))
    fig.update_layout(yaxis_title="Blocks")
    st.plotly_chart(style_fig(fig), use_container_width=True)

    # Assignment detail
    st.markdown("### Replica assignment")
    assign_rows = []
    for seg in se.segments:
        for nid in ae.segment_replicas.get(seg.segment_id, []):
            assign_rows.append({"Segment": seg.segment_id, "Node": nid})
    st.dataframe(pd.DataFrame(assign_rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# ── PAGE: Storage ────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def page_storage() -> None:
    st.title("💾 Storage")
    if not st.session_state.simulated:
        st.info("Run the simulation first.")
        return

    sm  = st.session_state.storage_metrics
    ae  = st.session_state.assignment_engine
    cfg = st.session_state.config

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1: stat_card("Full node", StorageMetrics.format_bytes(sm.full_node_bytes))
    with c2: stat_card("Avg segmented", StorageMetrics.format_bytes(sm.average_node_bytes))
    with c3: stat_card("Min segmented", StorageMetrics.format_bytes(sm.min_node_bytes))
    with c4: stat_card("Max segmented", StorageMetrics.format_bytes(sm.max_node_bytes))
    st.metric("Storage reduction", f"{sm.reduction_percentage:.1f}%")

    st.divider()

    # Per-node table
    st.markdown("### Per-node storage")
    rows = sm.get_per_node_rows(ae)
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Distribution histogram
    st.markdown("### Distribution of total bytes per node")
    totals = [n.total_bytes for n in ae.nodes]
    fig = go.Figure(go.Histogram(
        x=totals, nbinsx=20,
        marker_color="#0B6E6E", opacity=0.8,
    ))
    fig.add_vline(x=sm.full_node_bytes, line_dash="dash", line_color="#B4540A",
                  annotation_text="Full node", annotation_position="top right")
    fig.add_vline(x=sm.average_node_bytes, line_dash="dot", line_color="#4FD1C5",
                  annotation_text="Avg segmented")
    fig.update_layout(xaxis_title="Bytes", yaxis_title="Nodes")
    st.plotly_chart(style_fig(fig), use_container_width=True)

    # Saving vs replicas curve
    st.markdown("### Saving vs replica count (other params fixed)")
    B = cfg["num_blocks"]
    N = cfg["num_nodes"]
    H = cfg["header_size"]
    S = cfg["state_size"]
    D = cfg["block_data_size"]
    full_b = B * D + B * H + S
    ms = list(range(1, min(N, 20) + 1))
    savings = [(full_b - (m * B * D / N + B * H + S)) / full_b * 100 for m in ms]
    fig2 = go.Figure(go.Scatter(
        x=ms, y=savings, mode="lines+markers",
        line=dict(color="#0B6E6E", width=2.5),
        marker=dict(size=7),
    ))
    cur_m = cfg["replicas"]
    cur_s = (full_b - (cur_m * B * D / N + B * H + S)) / full_b * 100
    fig2.add_scatter(x=[cur_m], y=[cur_s], mode="markers",
                     marker=dict(size=12, color="#B4540A"),
                     name=f"Current (m={cur_m})")
    fig2.update_layout(xaxis_title="Replicas (m)", yaxis_title="Saving (%)")
    st.plotly_chart(style_fig(fig2), use_container_width=True)


# ---------------------------------------------------------------------------
# ── PAGE: Network ────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def page_network() -> None:
    st.title("🌐 Network")
    if not st.session_state.simulated:
        st.info("Run the simulation first.")
        return

    ae  = st.session_state.assignment_engine
    avail = st.session_state.availability_sim

    st.markdown("### Node map")
    st.caption("Each tile is one simulated node.  Coloured badges show stored segments.")

    # Failure controls
    mode = st.radio(
        "Failure scenario",
        ["All online", "Mark specific nodes offline"],
        horizontal=True,
    )

    if mode == "Mark specific nodes offline":
        all_ids = [n.node_id for n in ae.nodes]
        chosen_off = st.multiselect("Nodes to take offline", all_ids)
        if chosen_off:
            avail.simulate_node_failures(node_ids=chosen_off)
        else:
            avail.restore_all_nodes()

    # Draw node grid
    per_row = 6
    nodes = ae.nodes
    for row_start in range(0, len(nodes), per_row):
        cols = st.columns(per_row)
        for i, node in enumerate(nodes[row_start: row_start + per_row]):
            with cols[i]:
                segs = node.segment_ids
                status = "🟢" if node.is_online else "🔴"
                pills = " ".join(
                    f'<span class="seg-pill s{s[1]}">{s}</span>' for s in segs
                ) if segs else "<span style='color:gray'>none</span>"
                st.markdown(
                    f"**{status} {node.node_id}**<br>{pills}",
                    unsafe_allow_html=True,
                )

    # Segment replica status
    st.markdown("### Segment replica status")
    seg_rows = []
    for seg_id, holder_ids in ae.segment_replicas.items():
        online = sum(1 for nid in holder_ids if ae.get_node(nid).is_online)
        seg_rows.append({
            "Segment": seg_id,
            "Holders": ", ".join(holder_ids),
            "Online copies": online,
            "Status": "✅ OK" if online > 1 else ("⚠️ Critical" if online == 1 else "❌ Lost"),
        })
    st.dataframe(pd.DataFrame(seg_rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# ── PAGE: Availability ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def page_availability() -> None:
    st.title("📡 Availability")
    if not st.session_state.simulated:
        st.info("Run the simulation first.")
        return

    avail = st.session_state.availability_sim
    ae    = st.session_state.assignment_engine
    cfg   = st.session_state.config

    st.markdown("### Simulate random node failures")
    pct = st.slider("Failure percentage", 0, 100, 30, 5)
    seed_av = st.number_input("Failure seed", 0, 9999, cfg["seed"])

    result = avail.simulate_node_failures(
        failure_percentage=float(pct), seed=int(seed_av)
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1: stat_card("Total nodes",   str(result["total_nodes"]))
    with c2: stat_card("Online nodes",  str(result["online_nodes"]))
    with c3: stat_card("Offline nodes", str(result["offline_nodes"]))
    with c4: stat_card("Availability",  f"{result['availability_percentage']:.1f}%")

    # Per-segment bar
    st.markdown("### Surviving copies per segment")
    seg_ids  = list(result["surviving_replicas"].keys())
    survivors = list(result["surviving_replicas"].values())
    colors = []
    for s in survivors:
        colors.append("#16703A" if s > 1 else ("#A8480A" if s == 1 else "#B42318"))

    fig = go.Figure(go.Bar(
        x=seg_ids, y=survivors,
        marker_color=colors, text=survivors, textposition="outside",
    ))
    fig.add_hline(y=cfg["replicas"], line_dash="dash", line_color="#0B6E6E",
                  annotation_text=f"Target replicas ({cfg['replicas']})")
    fig.update_layout(yaxis_title="Online copies", yaxis_range=[0, cfg["replicas"] + 1])
    st.plotly_chart(style_fig(fig), use_container_width=True)

    if result["lost_segments"]:
        st.error(f"Lost segments: {', '.join(result['lost_segments'])}")
    if result["critical_segments"]:
        st.warning(f"Critical (1 copy left): {', '.join(result['critical_segments'])}")

    # Offline nodes list
    st.markdown("### Offline nodes")
    if result["failed_node_ids"]:
        st.write(", ".join(result["failed_node_ids"]))
    else:
        st.write("All nodes online.")

    # Sweep chart
    st.markdown("### Availability across failure rates (multi-run average)")
    st.caption(
        "Each point is the average of 50 random failure simulations at that rate. "
        "Individual runs jump in 20-point steps because there are only 5 segments."
    )
    import random as _random

    total_segs = len(ae.segment_replicas)
    pcts_sweep = list(range(0, 95, 5))
    avg_avail = []
    for p in pcts_sweep:
        runs = []
        for run_seed in range(50):
            r = avail.simulate_node_failures(
                failure_percentage=float(p), seed=run_seed
            )
            runs.append(r["availability_percentage"])
        avg_avail.append(sum(runs) / len(runs))
    # Restore
    avail.simulate_node_failures(failure_percentage=float(pct), seed=int(seed_av))

    fig2 = go.Figure(go.Scatter(
        x=pcts_sweep, y=avg_avail,
        mode="lines+markers",
        line=dict(color="#0B6E6E", width=2.5),
        fill="tozeroy", fillcolor="rgba(11,110,110,0.1)",
    ))
    fig2.update_layout(
        xaxis_title="Failure rate (%)",
        yaxis_title="Avg segment availability (%)",
        yaxis_range=[0, 105],
    )
    st.plotly_chart(style_fig(fig2), use_container_width=True)


# ---------------------------------------------------------------------------
# ── PAGE: Probability ────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def page_probability() -> None:
    st.title("📐 Probability")
    if not st.session_state.simulated:
        cfg_rep = 3; cfg_nodes = 30
    else:
        cfg_rep   = st.session_state.config["replicas"]
        cfg_nodes = st.session_state.config["num_nodes"]

    st.markdown(
        "**Formula:** P = (A / n)^m  —  the chance all *m* copies of a segment "
        "sit on adversary-controlled nodes."
    )

    col1, col2, col3 = st.columns(3)
    with col1: n = st.slider("Total nodes (n)", 5, 200, cfg_nodes)
    with col2: A = st.slider("Adversary nodes (A)", 1, max(1, n // 2), min(3, n // 2))
    with col3: m = st.slider("Replicas (m)", 1, 10, min(cfg_rep, 10))

    A = min(A, n)
    m = min(m, n)

    try:
        res = segment_loss_probability(n, A, m)
        ex  = exact_segment_loss_probability(n, A, m)
    except ValueError as e:
        st.error(str(e))
        return

    c1, c2 = st.columns(2)
    with c1:
        stat_card("Paper formula (P)", f"{res['probability']:.6f}")
        st.caption(res["formula_text"])
    with c2:
        stat_card("Exact (without replacement)", f"{ex:.6f}")
        st.caption("More precise; always ≤ formula")

    if res["probability"] > 0:
        st.info(
            f"About 1 in {1/res['probability']:,.0f} segments would be lost "
            f"to this attacker.  Exact: 1 in {(1/ex):,.0f}."
        )

    # Curve
    st.markdown("### Loss probability vs replicas (log scale)")
    curve = calculate_probability_curve(n, A, max_replicas=10)
    ms_c = [r["m"] for r in curve]
    ps_c = [r["probability"] for r in curve]
    ex_c = [exact_segment_loss_probability(n, A, r["m"]) for r in curve]

    fig = go.Figure()
    fig.add_scatter(x=ms_c, y=ps_c, name="Paper formula",
                    mode="lines+markers", line=dict(color="#0B6E6E", width=2.5))
    fig.add_scatter(x=ms_c, y=ex_c, name="Exact",
                    mode="lines+markers", line=dict(color="#B4540A", dash="dash", width=2))
    fig.add_scatter(x=[m], y=[res["probability"]], name="Current",
                    mode="markers", marker=dict(size=12, color="#6D3FC4"))
    fig.update_layout(
        xaxis_title="Replicas (m)",
        yaxis_title="Probability (log)",
        yaxis_type="log",
    )
    st.plotly_chart(style_fig(fig), use_container_width=True)

    # Multi-curve
    st.markdown("### Curves for different attacker sizes")
    pcts = [5, 10, 20, 33]
    multi = calculate_multiple_curves(n, pcts, max_replicas=10)
    fig2 = go.Figure()
    colors2 = ["#0B6E6E", "#B4540A", "#6D3FC4", "#B4235A"]
    for pct_val, color in zip(pcts, colors2):
        data_pts = multi.get(pct_val, [])
        if data_pts:
            fig2.add_scatter(
                x=[r["m"] for r in data_pts],
                y=[r["probability"] for r in data_pts],
                name=f"A={pct_val}% of n",
                mode="lines+markers",
                line=dict(color=color, width=2),
            )
    fig2.update_layout(
        xaxis_title="Replicas (m)",
        yaxis_title="Probability (log)",
        yaxis_type="log",
    )
    st.plotly_chart(style_fig(fig2), use_container_width=True)

    with st.expander("Assumptions"):
        st.text(get_assumptions_explanation())


# ---------------------------------------------------------------------------
# ── PAGE: Integrity ───────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def page_integrity() -> None:
    st.title("🔒 Integrity")
    if not st.session_state.simulated:
        st.info("Run the simulation first.")
        return

    ic  = st.session_state.integrity_checker
    bc  = st.session_state.blockchain
    cfg = st.session_state.config

    # Original chain status
    orig = ic.verify_original()
    if orig["valid"]:
        st.success("✅ Original chain: Valid — every block matches its fingerprints.")
    else:
        st.error(f"Original chain: {orig['error']}")

    st.divider()
    st.markdown("### Tamper experiments (on a copy — the real chain is never touched)")

    max_block = len(bc) - 1
    block_idx = st.slider("Target block index", 0, max_block, min(10, max_block))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔧 Change an amount (attacker rewrites own hash)"):
            res = ic.tamper_copy(block_idx, tx_index=0, new_amount=9_999.0)
            v   = res["verification"]
            st.json(res, expanded=True)
            if not v["valid"]:
                st.error(f"Caught at block {v['failed_block']}: {v['error']}")
            else:
                st.warning("Not caught — this is the last block; nothing references it yet.")

    with col2:
        if st.button("🔧 Replace previous_hash (attacker rewrites own hash)"):
            res = ic.tamper_previous_hash(block_idx)
            v   = res["verification"]
            st.json(res, expanded=True)
            if not v["valid"]:
                st.error(f"Caught at block {v['failed_block']}: {v['error']}")
            else:
                st.warning("Not caught.")

    st.markdown("#### Last-block tamper (should NOT be caught)")
    if st.button("🔧 Tamper last block"):
        res = ic.tamper_last_block(tx_index=0, new_amount=9_999.0)
        v   = res["verification"]
        st.json(res, expanded=True)
        if v["valid"]:
            st.success("As expected: last block not caught — no subsequent block references its hash.")
        else:
            st.error("Unexpectedly caught.")

    st.divider()
    st.markdown("### Run all three experiments at once")
    if st.button("▶ Run all integrity experiments"):
        all_res = ic.run_all_experiments(block_index=block_idx)
        for exp_name, exp_res in all_res.items():
            v = exp_res["verification"]
            icon = "❌" if not v["valid"] else "✅"
            st.markdown(f"**{exp_name}** — {icon} valid={v['valid']}  error={v.get('error')}")

    st.markdown(
        """
        <div class="sc-note">
        <strong>Note:</strong> The last block can never be caught by hash-chaining alone.
        Real systems rely on other nodes agreeing on the chain tip.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# ── PAGE: Export ─────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def page_export() -> None:
    st.title("📦 Export")
    if not st.session_state.simulated:
        st.info("Run the simulation first.")
        return

    exp = st.session_state.export_engine
    sm  = st.session_state.storage_metrics
    ae  = st.session_state.assignment_engine
    se  = st.session_state.segmentation_engine
    avail = st.session_state.availability_sim
    cfg   = st.session_state.config

    st.markdown(
        "Files are saved to the folder where you started Streamlit.  "
        "Every JSON includes `simulation_only: true` and a disclaimer."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Scenario JSON"):
            results = sm.compare_storage()
            path = exp.export_results_json(cfg, results)
            st.success(f"Saved: `{path}`")

        if st.button("📊 Node assignments CSV"):
            rows = []
            for seg_id, node_ids in ae.segment_replicas.items():
                for nid in node_ids:
                    rows.append({"segment": seg_id, "node": nid})
            path = exp.export_node_assignment_csv(rows)
            st.success(f"Saved: `{path}`")

        if st.button("💾 Storage metrics CSV"):
            rows = sm.get_per_node_rows(ae)
            path = exp.export_storage_metrics_csv(rows)
            st.success(f"Saved: `{path}`")

    with col2:
        if st.button("📋 Complete report JSON"):
            storage = sm.compare_storage()
            prob_res = {
                m: segment_loss_probability(cfg["num_nodes"], max(1, cfg["num_nodes"] // 10), m)
                for m in range(1, cfg["replicas"] + 1)
            }
            av_rows = []
            for p in [0, 10, 20, 30, 40, 50, 60]:
                r = avail.simulate_node_failures(
                    failure_percentage=float(p), seed=cfg["seed"]
                )
                av_rows.append({"failure_pct": p, **r})
            path = exp.create_experiment_report(cfg, storage, av_rows, prob_res)
            st.success(f"Saved: `{path}`")

        if st.button("📑 Segment summary CSV"):
            rows = se.summary()
            path = exp.export_segment_summary_csv(rows)
            st.success(f"Saved: `{path}`")

    st.divider()
    st.markdown(
        "_Export page buttons: Scenario (JSON), Assignments (CSV), Storage (CSV), Complete report (JSON)._"
    )


# ---------------------------------------------------------------------------
# ── Main router ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

PAGES = {
    "Dashboard":    page_dashboard,
    "Segments":     page_segments,
    "Storage":      page_storage,
    "Network":      page_network,
    "Availability": page_availability,
    "Probability":  page_probability,
    "Integrity":    page_integrity,
    "Export":       page_export,
}

ICONS = {
    "Dashboard":    "🏠",
    "Segments":     "🔪",
    "Storage":      "💾",
    "Network":      "🌐",
    "Availability": "📡",
    "Probability":  "📐",
    "Integrity":    "🔒",
    "Export":       "📦",
}


def main() -> None:
    initialize_session_state()
    inject_css()
    sidebar()

    # Page navigation using tabs in the sidebar bottom
    st.sidebar.divider()
    st.sidebar.markdown("### Navigate")
    page_name = st.sidebar.radio(
        "Page",
        list(PAGES.keys()),
        format_func=lambda k: f"{ICONS[k]} {k}",
        label_visibility="collapsed",
    )

    PAGES[page_name]()


if __name__ == "__main__":
    main()
