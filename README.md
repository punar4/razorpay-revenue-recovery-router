# Autonomous Revenue Recovery Router (AR3)

> **Track 3: AI Revenue Recovery | Razorpay AI Buildathon**
> A high-throughput telemetry diagnostic, bounded fallback, and settlement recovery router built with **Gemini 2.5 Flash**, **Pydantic v2**, and deterministic FinTech circuit breakers.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg?logo=python\&logoColor=white)](https://www.python.org/)
[![Gemini 2.5 Flash](https://img.shields.io/badge/Model-Gemini%202.5%20Flash-4E75F6.svg?logo=google\&logoColor=white)](https://ai.google.dev/)
[![Pydantic v2](https://img.shields.io/badge/Validation-Pydantic%20v2-E92063.svg?logo=pydantic\&logoColor=white)](https://docs.pydantic.dev/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg?logo=streamlit\&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

##  Problem Space & The Recovery Gap

In high-concurrency digital payment ecosystems across **UPI, IMPS, and domestic card acquiring networks in India**, payment infrastructure can degrade non-linearly under peak volume.

Core Banking Systems (CBS) may experience intermittent timeouts, network switches can throttle connections, and PSPs can emit unmapped internal error strings.

When transactions fail, checkout systems commonly fall into two problematic extremes:

```text
                         ┌──────────────────────────────┐
                         │   Payment Attempt Declines   │
                         └──────────────┬───────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
       [ Immediate Cart Abandon ]                [ Blind Retries ]
                    │                                       │
                    ▼                                       ▼
          Merchant GMV Leakage                    Switch Congestion
                                                        │
                                                        ▼
                                             Duplicate Debit Risk
```

### The Recovery Gap

**1. Immediate Passive Surrender**

Checkout orchestrators can treat non-terminal network failures as permanent declines and abandon the transaction. This creates potentially recoverable GMV leakage.

**2. Aggressive Blind Retrying**

Repeatedly sending identical payment payloads without appropriate backoff can increase switch congestion, trigger rate limits, and create duplicate-debit hazards.

### AR3's Approach

AR3 bridges this gap through **engineering-first AI restraint**:

* Deterministic terminal errors are handled locally.
* Ambiguous telemetry is escalated to Gemini 2.5 Flash.
* Gemini outputs are constrained to a typed recovery schema.
* Deterministic FinTech circuit breakers can override unsafe recommendations.
* Recovery dispatches use deterministic idempotency keys.
* Settlement estimates incorporate rail-specific success probabilities.

The core principle is simple:

> **AI diagnoses. Deterministic rules decide.**

---

#  End-to-End System Architecture

AR3 separates deterministic operational logic from non-deterministic generative inference.

```text
┌──────────────────────────────────────────────────────────────┐
│              Incoming Payment Telemetry Stream               │
│       Raw ISO-8583 Codes / Core Banking Logs / Errors        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              Tier-1 Deterministic Fast-Path                  │
│                 In-memory error classification               │
└──────────────────────┬───────────────────────┬───────────────┘
                       │                       │
              Fatal State Code        Cryptic / Network Error
                       │                       │
                       ▼                       ▼
          ┌────────────────────┐   ┌───────────────────────────┐
          │   Immediate HALT   │   │ Tier-2 LLM Escalation     │
          │                    │   │                           │
          │ • No LLM call      │   │ Gemini 2.5 Flash          │
          │ • No retry         │   │ Pydantic JSON Schema      │
          │ • Immediate UI     │   │ Structured diagnosis      │
          └────────────────────┘   └──────────────┬────────────┘
                                                  │
                                                  ▼
                                   ┌───────────────────────────┐
                                   │ FinTech Circuit Breakers  │
                                   │                           │
                                   │ • Hard invariants         │
                                   │ • Mandatory backoffs      │
                                   │ • Rail overrides          │
                                   │ • Retry suppression       │
                                   └──────────────┬────────────┘
                                                  │
                                                  ▼
                                   ┌───────────────────────────┐
                                   │ Idempotent Dispatch       │
                                   │                           │
                                   │ idemp_<txn_id>_<rail>     │
                                   └──────────────┬────────────┘
                                                  │
                                                  ▼
                                   ┌───────────────────────────┐
                                   │ Verified Settlement       │
                                   │                           │
                                   │ Card:       ~85%          │
                                   │ NetBanking: ~79.5%        │
                                   │ UPI:        ~72%          │
                                   └───────────────────────────┘
```

---

#  Core Engineering Pillars

## Core Decision Flow

AR3 follows a simple principle: **deterministic rules control financial safety, while Gemini provides structured diagnosis for ambiguous failures.**

The model can recommend a recovery strategy, but deterministic circuit breakers retain final authority over retries, delays, and rail selection.

```python
def recover_transaction(telemetry, amount, txn_id):
    # Tier 1: deterministic fast-path
    if telemetry.error_code in {"INSUFFICIENT_FUNDS", "ACCOUNT_CLOSED"}:
        return {
            "action": "HALT",
            "reason": "terminal_decline",
            "retry": False,
        }

    # Tier 2: Gemini produces a structured recommendation.
    directive = llm_diagnose(telemetry)

    # Deterministic safety layer always has final authority.
    if telemetry.error_code in {"CBS_504_GW_TIMEOUT", "RC_91"}:
        directive.backoff_delay_minutes = max(
            directive.backoff_delay_minutes, 15
        )

    if telemetry.error_code == "U30":
        directive.alternate_rail = (
            "CARD" if telemetry.channel == "UPI" else "NETBANKING"
        )

    if amount > 50_000:
        directive.backoff_delay_minutes = max(
            directive.backoff_delay_minutes, 30
        )

    # Every dispatch gets a deterministic idempotency key.
    idempotency_key = f"idemp_{txn_id}_{directive.alternate_rail}"

    return {
        "action": "RECOVER",
        "rail": directive.alternate_rail,
        "backoff_minutes": directive.backoff_delay_minutes,
        "idempotency_key": idempotency_key,
        "user_copy": directive.user_copy,
    }
```

> `llm_diagnose()` represents the Gemini + Pydantic structured inference layer implemented in the project.

---

## 1. Tier-1 Deterministic Fast-Path

The system enforces that generative models must not evaluate deterministic terminal decline codes.

Fatal states such as:

* `INSUFFICIENT_FUNDS`
* `ACCOUNT_CLOSED`
* malformed VPAs

are evaluated locally in memory.

### Design Goals

| Property         |                 Target |
| ---------------- | ---------------------: |
| LLM Calls        |  0 for terminal errors |
| Token Cost       | $0 for terminal errors |
| Processing       |              In-memory |
| Latency Overhead |               < 0.1 ms |

This prevents unnecessary model calls across high-frequency fatal declines.

---

## 2. Tier-2 LLM Telemetry Escalation

Ambiguous bank errors, raw Core Banking System logs, and ISO-8583/network failures are escalated to **Gemini 2.5 Flash**.

Examples include:

* Response Code `91` - System Inoperative
* HTTP `504` timeouts
* `CBS_504_GW_TIMEOUT`
* cryptic PSP error strings
* transient network failures

Gemini is constrained to a typed Pydantic v2 response schema.

### Recovery Directive

The model produces structured fields rather than free-form operational instructions:

```text
root_cause
alternate_rail
backoff_delay_minutes
user_copy
```

The expected rail values are:

```text
UPI
CARD
NETBANKING
NONE
```

This keeps the AI layer focused on diagnosis and bounded recovery recommendations.

---

#  3. FinTech Circuit Breakers

Generative AI outputs do **not** hold final dispatch authority.

Every recovery directive passes through deterministic safety rules before execution.

| Breaker                           | Trigger                    | Enforcement                   |
| --------------------------------- | -------------------------- | ----------------------------- |
| `MANDATORY_CBS_504_BACKOFF`       | CBS timeout / RC-91        | Minimum 15-minute backoff     |
| `BLOCK_REDUNDANT_VPA_SUBMISSION`  | U30 / VPA velocity ceiling | Redirect to Card / NetBanking |
| `HALT_INSUFFICIENT_BALANCE_RETRY` | Zero-balance state         | Suppress retries              |
| `HIGH_VALUE_TRANSACTION_THROTTLE` | Amount > ₹50,000           | Minimum 30-minute buffer      |

### Why this matters

The model may suggest a 2-minute retry delay for a temporary switch failure.

AR3 can deterministically override that recommendation to 15 minutes.

This creates a hard boundary between:

```text
AI Recommendation
       │
       ▼
Safety Validation
       │
       ▼
Final Dispatch Decision
```

The AI is therefore useful without becoming the final authority over financial operations.

---

#  4. Idempotent Dispatch & Verified Settlement

Every recovery dispatch receives a deterministic idempotency key:

```text
idemp_<txn_id>_<target_rail>
```

For example:

```text
idemp_TXN_ICICI_88319_UPI
```

Downstream gateways can use this key to recognize repeated requests after transient connection failures and reduce duplicate-dispatch risk.

---

## Verified Settlement Yield Modeling

AR3 does not assume that every rerouted transaction succeeds.

The recovery engine uses rail-specific settlement probabilities:

| Recovery Rail | Settlement Yield |
| ------------- | ---------------: |
| Card          |            85.0% |
| NetBanking    |            79.5% |
| Secondary UPI |            72.0% |

The expected verified recovery is modeled as:

```text
Verified Settled GMV
=
Σ (Scheduled GMV × P(Settlement | Rail))
```

This provides a more conservative recovery estimate than assuming 100% success after failover.

---

# Sample Execution Trace

### Incoming Telemetry

```text
TXN_ID: TXN_ICICI_88319
Timestamp: 2026-09-09T12:30:00Z
Channel: UPI
Error Log: "CBS_504_GW_TIMEOUT: Core switch did not acknowledge ISO-8583 pack within 30000ms"
Amount: INR 18,500.00
Customer VPA: user@okhdfcbank
```

### Pipeline Execution

**1. Tier-1 Fast-Path**

The error is not recognized as a deterministic terminal decline, so it is forwarded to Tier-2.

**2. Tier-2 Gemini Diagnosis**

```text
root_cause:
"Issuing core banking switch unavailable."

alternate_rail:
"UPI"

backoff_delay_minutes:
2
```

**3. Circuit Breaker Override**

```text
Rule:
MANDATORY_CBS_504_BACKOFF

Model delay:
2 minutes

Enforced delay:
15 minutes
```

**4. Idempotent Dispatch**

```text
idemp_TXN_ICICI_88319_UPI
```

**5. Probabilistic Settlement**

```text
Rail Applied:
UPI

Settlement Yield:
72.0%

Verified Recovery GMV:
INR 13,320.00
```

This example demonstrates the central AR3 workflow:

> **Detect → Diagnose → Veto unsafe behavior → Dispatch idempotently → Estimate verified recovery**

---

# Repository Structure

```text
razorpay-revenue-recovery-router/
│
├── app.py
│   └── Streamlit operational dashboard & telemetry visualization
│
├── engine.py
│   └── Dual-tier router, circuit breaker veto layer & recovery math
│
├── schemas.py
│   └── Pydantic v2 models enforcing structured AI outputs
│
├── telemetry_dataset.json
│   └── Synthetic dataset of 50+ Indian banking error logs
│
├── requirements.txt
│   └── Production dependencies
│
├── .env.example
│   └── Environment template for Gemini API credentials
│
└── README.md
    └── System architecture & operational documentation
```

---

# Setup & Local Execution

## 1. Clone the Repository

```bash
git clone https://github.com/punar4/razorpay-revenue-recovery-router.git
cd razorpay-revenue-recovery-router
```

## 2. Create a Virtual Environment

```bash
python -m venv venv
```

### macOS / Linux

```bash
source venv/bin/activate
```

### Windows

```powershell
.\venv\Scripts\Activate.ps1
```

## 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Or manually:

```bash
pip install streamlit pandas pydantic google-genai python-dotenv
```

## 4. Configure Gemini

Create a `.env` file in the project root:

```env
GEMINI_API_KEY="your-gemini-api-key-here"
```

## 5. Launch the Dashboard

```bash
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

The dashboard can be used to visualize telemetry and trigger batch recovery processing.

---

#  Live Dashboard Metrics

The Streamlit dashboard exposes the following operational metrics.

### Gross Volume at Risk

Total transaction volume of failed checkouts processed across the batch.

### Scheduled Recovery GMV

Amount safely queued for secondary remediation after passing validation checks.

### Verified Settled Recovery

Expected settlement value after applying rail-specific settlement probabilities.

### Token Efficiency Index

Tracks the token usage avoided by resolving deterministic fatal error states locally instead of invoking the LLM.

---

#  Production FinTech Guarantees

## Zero Unnecessary LLM Calls

Deterministic terminal failures are resolved locally without sending them through the generative layer.

## Idempotent Recovery Dispatch

Deterministic idempotency keys are generated for recovery attempts to reduce duplicate-dispatch risk.

## Graceful Degradation

If an external LLM call times out, the system falls back to deterministic handling rather than leaving the transaction in an unhandled state.

## Data Sanitization

PII, user account identifiers, and cardholder data are scrubbed before telemetry payloads are sent to the model layer.

## Deterministic Safety Authority

AI recommendations are always evaluated by deterministic circuit breakers before recovery dispatch.

---

#  Why AR3?

Traditional retry systems generally answer:

> **"Should we retry?"**

AR3 attempts to answer a richer set of questions:

```text
What caused the failure?
        │
        ▼
Is the failure recoverable?
        │
        ▼
Should we wait before retrying?
        │
        ▼
Which payment rail is safer?
        │
        ▼
Can the recovery be dispatched idempotently?
        │
        ▼
What recovery GMV can realistically be expected?
```

The important architectural distinction is:

> **Gemini provides diagnosis and recommendations. Deterministic FinTech rules retain control over execution.**

This makes the system suitable for experimentation with AI-assisted payment recovery without allowing unconstrained model output to directly control financial retries.

---

#  Submission Details

**Track:** Track 3: AI Revenue Recovery — Razorpay AI Buildathon

**Project:** Autonomous Revenue Recovery Router (AR3)

**Author:** Punar (@punar4)

**Repository:** `punar4/razorpay-revenue-recovery-router`

---

