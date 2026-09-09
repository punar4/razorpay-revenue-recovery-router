# Autonomous Revenue Recovery Router (AR3)

> **Track 3: AI Revenue Recovery** — Razorpay AI Buildathon  
> A high-throughput telemetry diagnostic, bounded fallback, and settlement recovery router built with Gemini 2.5 Flash and deterministic FinTech circuit breakers.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Gemini 2.5 Flash](https://img.shields.io/badge/Model-Gemini%202.5%20Flash-4E75F6.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Pydantic v2](https://img.shields.io/badge/Validation-Pydantic%20v2-E92063.svg?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 Problem Space & The Recovery Gap

In high-concurrency digital payment ecosystems—specifically across Unified Payments Interface (UPI), IMPS, and domestic Card acquiring networks in India—payment infrastructure degrades non-linearly under peak volume. Core Banking Systems (CBS) experience intermittent timeouts, network switches throttle connections, and PSPs emit unmapped internal error strings.

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

```


Immediate Passive Surrender (GMV Leakage): Checkout orchestrators treat non-terminal network hiccups as hard fatal drops, dumping the cart. Merchants bleed between 15% and 28% of recoverable GMV.

Aggressive Blind Retrying (Switch Congestion & Double Charges): Systems hammer identical payment payloads without backoffs. This triggers NPCI rate limits, risks switch blacklisting, and causes disastrous duplicate customer debits.

AR3 bridges this gap through engineering-first AI restraint: terminal errors drop instantly with zero latency and zero token cost, while ambiguous, degraded errors receive structured LLM root-cause remediation protected by hard FinTech safety circuit breakers.

------------------------------------------------------------------------------------------------------------------------------------------------------------------

End-to-End System Architecture
AR3 separates deterministic operational logic from non-deterministic generative inference:
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
                   │ • Zero Latency(<0.1ms)│  │ (Gemini 2.5 Flash API)            │
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



Core Engineering Pillars
1. Tier-1 Deterministic Fast-Path (0ms Latency, Zero Token Cost)
The system enforces that generative models must never evaluate deterministic, terminal decline codes.

Fatal states—such as INSUFFICIENT_FUNDS, ACCOUNT_CLOSED, or malformed VPAs—are evaluated locally in-memory.

Latency Overhead: < 0.1 ms.

Token Cost: $0.00, eliminating token waste across high-frequency fatal declines.

2. Tier-2 LLM Telemetry Escalation (Gemini 2.5 Flash)
Ambiguous bank errors, raw Core Banking System (CBS) logs, and ISO-8583 response codes (e.g., Response Code 91 - System Inoperative, HTTP 504 timeouts) escalate to Gemini 2.5 Flash.

The LLM is bound strictly to a typed Pydantic v2 schema via response_mime_type="application/json" and response_schema=RecoveryDirective, eliminating hallucinations or prose drift:

from pydantic import BaseModel, Field
from typing import Literal

class RecoveryDirective(BaseModel):
    root_cause: str = Field(..., description="Technical diagnosis of upstream failure")
    alternate_rail: Literal["UPI", "CARD", "NETBANKING", "NONE"] = Field(..., description="Suggested failover rail")
    backoff_delay_minutes: int = Field(..., ge=0, le=120, description="Mandatory backoff wait time prior to retry")
    user_copy: str = Field(..., description="User-facing remediation message for checkout UI")



3. FinTech Circuit Breakers (Absolute Safety Veto Layer)Generative AI outputs do not hold final dispatch authority. A deterministic rule layer evaluates every directive and enforces hard financial invariants:Breaker CodeInvariant ConditionEnforcement ActionMANDATORY_CBS_504_BACKOFFBank switch returns Core Banking System timeout (504 / RC-91).Overrides lower model delays; enforces a mandatory 15-minute wait to prevent switch DDoS.BLOCK_REDUNDANT_VPA_SUBMISSIONTelemetry flags an NPCI VPA velocity ceiling (U30).Forcibly reassigns the rail to Card / NetBanking; blocks repeated attempts on the exhausted VPA.HALT_INSUFFICIENT_BALANCE_RETRYFast-path or log reveals zero-balance state.Immediate execution suppression (0 retries). Prevents issuer decline penalties and customer fees.HIGH_VALUE_TRANSACTION_THROTTLETicket amount > ₹50,000.Automatically schedules a mandatory 30-minute buffer to avoid high-ticket switch contention.

4. Idempotent Dispatch & Verified Yield SettlementEvery recovery dispatch requires a deterministic, cryptographically unique idempotency key:idempotency_key = idemp_<txn_id>_<target_rail>Downstream gateways recognize repeated tokens on transient connection resets, ensuring zero duplicate debit risk.Realistic Settlement Yield ModelingStandard hackathon pitches assume 100% of rerouted retries succeed. AR3 calculates realistic recovered GMV using empirical secondary-rail settlement yields:Credit/Debit Card Failovers: 85.0% settlement success rate.NetBanking Failovers: 79.5% settlement success rate.Secondary UPI Attempts: 72.0% settlement success rate.$$\text{Verified Settled GMV} = \sum_{i=1}^{N} \left( \text{Scheduled GMV}_i \times P(\text{Settlement} \mid \text{Rail}_i) \right)$$


Sample Execution Trace
Plaintext
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



Repository Structure - 
Plaintext
razorpay-revenue-recovery-router/
├── app.py                     # Streamlit operational dashboard & telemetry visualization
├── engine.py                  # Dual-tier router, circuit breaker veto layer, & recovery math
├── schemas.py                 # Pydantic v2 data models enforcing strict JSON outputs
├── telemetry_dataset.json     # Synthetic dataset of 50+ real-world Indian banking error logs
├── requirements.txt           # Pinned production dependencies
├── .env.example               # Environment template for Google Gemini API credentials
└── README.md                  # System architecture and operational documentation



Setup & Local Execution
1. Clone & Setup Virtual Environment
Bash
git clone [https://github.com/punar4/razorpay-revenue-recovery-router.git](https://github.com/punar4/razorpay-revenue-recovery-router.git)
cd razorpay-revenue-recovery-router
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
.\venv\Scripts\Activate.ps1
2. Install Dependencies
Bash
pip install --upgrade pip
pip install -r requirements.txt
(Or install manually: pip install streamlit pandas pydantic google-genai python-dotenv)

3. Configure API Credentials
Create a .env file in the project root:

Code snippet
GEMINI_API_KEY="your-gemini-api-key-here"
4. Launch the Dashboard
Bash
streamlit run app.py
Open http://localhost:8501 to view the live dashboard and trigger batch recoveries.



Live Dashboard Metrics Explained - 
Gross Volume at Risk: Total transaction volume of failed checkouts processed across the batch.

Scheduled Recovery GMV: Amount safely queued for secondary remediation after passing validation checks.

Verified Settled Recovery: Expected settlement yield after applying rail-specific success probabilities (70%–85%).

Token Efficiency Index: Total tokens saved by resolving fatal error states locally in memory.



Production FinTech Guarantees - 
Zero Duplicate Debits: Enforced downstream via deterministic idempotency keys.

Graceful Degradation: If external LLM calls time out, system defaults to static deterministic backoff instead of failing unhandled.

Data Sanitization: PII, user account identifiers, and cardholder data are scrubbed before payload telemetry prompts are generated.



Submission Details - 
Track: Track 3: AI Revenue Recovery — Razorpay AI Buildathon

Project Name: Autonomous Revenue Recovery Router (AR3)

Author: Punar (@punar4)

Repository: punar4/razorpay-revenue-recovery-router
