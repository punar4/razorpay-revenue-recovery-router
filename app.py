import streamlit as st
import pandas as pd
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from engine import process_recovery

# Borderless split circle: Electric Blue right half, Deep Navy left half
svg_circle = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <clipPath id="left-cut">
      <rect x="0" y="0" width="32" height="64"/>
    </clipPath>
  </defs>
  <circle cx="32" cy="32" r="30" fill="#0284C7"/>
  <circle cx="32" cy="32" r="30" fill="#0C2340" clip-path="url(#left-cut)"/>
</svg>"""

b64_icon = f"data:image/svg+xml;base64,{base64.b64encode(svg_circle.encode()).decode()}"

st.set_page_config(
    page_title="Autonomous Revenue Recovery Router",
    page_icon=b64_icon,
    layout="wide"
)

# Header Section
col_head, col_status = st.columns([3, 1])
with col_head:
    st.title("Autonomous Revenue Recovery Engine")
    st.caption("Track 03: AI Revenue Recovery — Telemetry Diagnostic & Bounded Fallback Engine")
with col_status:
    st.write("")
    st.success("● Pipeline Active (Tier-1 + Tier-2)")

st.divider()

# Sidebar Configuration
with st.sidebar:
    st.header("Batch Configuration")
    batch_size = st.slider("Sample Records to Ingest", min_value=5, max_value=50, value=20, step=5)
    st.divider()
    st.subheader("Architecture")
    st.markdown("""
    - **Tier 1**: Deterministic Fast-Path (0ms)
    - **Tier 2**: Gemini Structured Fallback
    - **Safety**: Multi-Rule Circuit Breakers
    - **Audit**: Idempotent Execution Ledger
    """)

# Load benchmark telemetry
try:
    df_raw = pd.read_csv("failed_transactions.csv")
except FileNotFoundError:
    st.error("failed_transactions.csv not found! Run dataset.py first.")
    st.stop()

st.subheader("Ingested Telemetry Feed (Failed Transactions)")
st.dataframe(df_raw.head(batch_size), use_container_width=True, hide_index=True)

if st.button("Trigger Recovery Pipeline", type="primary"):
    with st.spinner("Processing telemetry batch through diagnostic rails & settlement verification..."):
        records = df_raw.head(batch_size).to_dict(orient="records")
        results = []
        progress_bar = st.progress(0)

        max_workers = min(5, len(records))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_txn = {executor.submit(process_recovery, txn): txn for txn in records}
            completed_count = 0
            for future in as_completed(future_to_txn):
                results.append(future.result())
                completed_count += 1
                progress_bar.progress(completed_count / len(records))

        res_df = pd.DataFrame(results)
        res_df["sort_key"] = res_df["txn_id"].apply(lambda x: int(x.split("_")[-1]))
        res_df = res_df.sort_values("sort_key").drop(columns=["sort_key"])

        # Financial & Settlement Math
        total_at_risk = res_df["amount_inr"].sum()
        recoverable_df = res_df[res_df["suggested_rail"] != "HALT"]
        scheduled_gmv = recoverable_df["amount_inr"].sum()
        actual_settled_gmv = res_df["settled_amount"].sum()
        overrides_count = int(res_df["circuit_breaker_triggered"].sum())
        settlement_rate = (actual_settled_gmv / total_at_risk * 100) if total_at_risk > 0 else 0

        st.divider()
        st.subheader("Measured Settlement & Guardrail Analytics")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Gross Volume at Risk", f"₹{total_at_risk:,.2f}")
        m2.metric("Scheduled Recovery GMV", f"₹{scheduled_gmv:,.2f}")
        m3.metric("Verified Settled Recovery", f"₹{actual_settled_gmv:,.2f}", delta=f"{settlement_rate:.1f}% Recovery Yield")
        m4.metric("Circuit Breaker Overrides", f"{overrides_count}")

        st.divider()
        st.subheader("Recovery Routing Ledger & Dispatch Audit Trail")

        def highlight_breaker_overrides(row):
            if row["circuit_breaker_triggered"]:
                return ["background-color: rgba(239, 68, 68, 0.2); color: #fca5a5; font-weight: bold;"] * len(row)
            return [""] * len(row)

        display_cols = [
            "txn_id", "bank", "error_code", "amount_inr", 
            "suggested_rail", "delay_minutes", "circuit_breaker_triggered", 
            "breaker_reason", "dispatch_status", "settlement_status",
            "idempotency_key", "customer_message"
        ]

        st.dataframe(
            res_df[display_cols].style.apply(highlight_breaker_overrides, axis=1),
            use_container_width=True,
            hide_index=True
        )

        st.caption(f"✓ Audited {len(res_df)} transaction telemetry events with idempotent dispatch keys and verified settlement execution.")