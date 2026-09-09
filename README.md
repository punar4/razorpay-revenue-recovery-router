# Autonomous Revenue Recovery Router

> **Track 3**: AI Revenue Recovery — Razorpay AI Buildathon  
> A resilient, dual-tier payment telemetry router combining a 0ms deterministic fast-path with Gemini 2.5 Flash root-cause diagnosis, strict FinTech safety circuit breakers, and idempotent multi-rail settlement verification.

---

## 📌 Executive Summary & Problem Space

In high-concurrency digital payment ecosystems—specifically across Unified Payments Interface (UPI), IMPS, and domestic Card acquiring networks in India—payment infrastructure frequently degrades during traffic spikes. Core Banking Systems (CBS) experience intermittent timeouts, network switches throttle connections, and PSPs emit unmapped internal error strings.

When transactions fail, modern checkout flows default to one of two broken extremes:

```text
                            ┌──────────────────────────────┐
                            │   Payment Attempt Declines   │
                            └──────────────┬───────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
        [ Current Default Path A ]                    [ Current Default Path B ]
          Immediate Cart Abandon                         Aggressive Blind Retries
                    │                                             │
                    ▼                                             ▼
     Severe Merchant GMV Leakage                   Exacerbates Switch Congestion
   (15% to 28% Addressable Loss)                  Spikes Duplicate Debit Hazards


┌──────────────────────────────────────────────┐
                  │    Incoming Payment Telemetry Stream         │
                  │  (Raw ISO-8583 Codes / Core Banking Dumps)   │
                  └───────────────────────┬──────────────────────┘
                                          │
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │       Tier-1 Deterministic Fast-Path         │
                  │        (0ms In-Memory Memory Lookup)         │
                  └───────────────┬──────────────────────┬───────┘
                                  │                      │
             [Fatal State Code]   │                      │   [Cryptic Log / Network Dropout]
                                  │                      │
                                  ▼                      ▼
                   ┌───────────────────────┐  ┌───────────────────────────────────┐
                   │ Immediate Halt (Drop) │  │ Tier-2 LLM Telemetry Escalation   │
                   │ • Zero Latency (<0.1ms)│  │ (Gemini 2.5 Flash API)            │
                   │ • Zero Token Overhead │  │ • Strict Pydantic JSON Schema     │
                   │ • Instant Client UI   │  └─────────────────┬─────────────────┘
                   └───────────────────────┘                    │
                                                                ▼
                                              ┌───────────────────────────────────┐
                                              │  FinTech Circuit Breakers (Veto)  │
                                              │  • Hard Invariant Safety Checks   │
                                              │  • Non-Negotiable Delay Enforcers │
                                              └─────────────────┬─────────────────┘
                                                                │
                                                                ▼
                                              ┌───────────────────────────────────┐
                                              │   Idempotent Dispatch Generator   │
                                              │   Key: `idemp_<txn_id>_<rail>`    │
                                              └─────────────────┬─────────────────┘
                                                                │
                                                                ▼
                                              ┌───────────────────────────────────┐
                                              │   Verified Settlement Pipeline    │
                                              │  • Card Switch Yield: ~85%        │
                                              │  • Secondary UPI Yield: ~72%      │
                                              └───────────────────────────────────┘


from pydantic import BaseModel, Field
from typing import Literal

class RecoveryDirective(BaseModel):
    root_cause: str = Field(..., description="Technical diagnosis of upstream failure")
    alternate_rail: Literal["UPI", "CARD", "NETBANKING", "NONE"] = Field(..., description="Suggested failover rail")
    backoff_delay_minutes: int = Field(..., ge=0, le=120, description="Mandatory backoff wait time prior to retry")
    user_copy: str = Field(..., description="User-facing remediation message for checkout UI")


[Incoming Telemetry Log]
TXN_ID: TXN_ICICI_88319
Timestamp: 2026-09-09T12:30:00Z
Channel: UPI
Error Log: "CBS_504_GW_TIMEOUT: Core switch did not acknowledge ISO-8583 pack within 30000ms"
Amount: INR 18,500.00
Customer VPA: user@okhdfcbank

[Pipeline Execution Trace]
1. Tier-1 Fast-Path: Unmapped 504 network error. Forwarded to Tier-2.
2. Tier-2 Reasoning (Gemini 2.5 Flash):
   - root_cause: "Issuing core banking switch unavailable."
   - alternate_rail: "UPI"
   - backoff_delay_minutes: 2
3. Circuit Breaker Override Triggered:
   - Rule Fired: 'MANDATORY_CBS_504_BACKOFF'
   - Override Action: Delay increased from 2m to 15m.
   - Idempotency Key: idemp_TXN_ICICI_88319_UPI
4. Probabilistic Settlement Engine:
   - Rail Applied: UPI (72.0% yield)
   - Verified Recovery GMV: INR 13,320.00


razorpay-revenue-recovery-router/
├── app.py                     # Streamlit operational dashboard & telemetry visualization
├── engine.py                  # Dual-tier router, circuit breaker veto layer, & recovery math
├── schemas.py                 # Pydantic v2 data models enforcing strict JSON outputs
├── telemetry_dataset.json     # Synthetic dataset of 50+ real-world Indian banking error logs
├── requirements.txt           # Pinned production dependencies
├── .env.example               # Environment template for Google Gemini API credentials
└── README.md                  # System architecture and operational documentation
