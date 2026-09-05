# Autonomous Revenue Recovery Router

> **Track 3**: AI Revenue Recovery — Razorpay AI Buildathon  
> A high-throughput telemetry diagnostic, bounded fallback, and settlement recovery router built with Gemini 2.5 Flash and deterministic FinTech circuit breakers.

---

## System Architecture

1. **Tier-1 Deterministic Fast-Path (0ms Latency, Zero Token Cost)**:
   - Evaluates terminal error codes (e.g., `INSUFFICIENT_FUNDS`, known velocity caps) instantly without external LLM calls.
2. **Tier-2 LLM Telemetry Escalation (Gemini 2.5 Flash)**:
   - Translates raw bank error codes, ISO-8583 specs, and CBS network logs into typed diagnostic remediation payloads using strict Pydantic JSON schemas.
3. **FinTech Circuit Breakers (Absolute Safety Veto)**:
   - Enforces hard banking invariants (mandatory 15m CBS 504 backoffs, UPI velocity reroutes to Card, zero-balance execution suppression, high-value transaction throttles) over arbitrary model outputs.
4. **Idempotent Dispatch & Verified Settlement**:
   - Simulates empirical secondary-rail settlement yields (70–85%) with tamper-proof idempotency keys to ensure zero double-charge risk.

---

## Setup & Local Execution

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/punar4/razorpay-revenue-recovery-router.git
cd razorpay-revenue-recovery-router
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
