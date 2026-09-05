import os
import json
import random
from typing import Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

class RecoveryPlan(BaseModel):
    root_cause: str = Field(description="Root cause failure classification.")
    suggested_rail: Literal["UPI", "CARD", "NETBANKING", "RETRY_SAME_RAIL", "HALT"] = Field(
        description="Target recovery routing rail."
    )
    delay_minutes: int = Field(description="Retry backoff interval in minutes.")
    customer_message: str = Field(description="Customer-facing remediation notification copy.")

client = genai.Client()

def call_gemini_recovery(txn: dict) -> dict:
    prompt = f"""
Analyze this failed payment telemetry event and output a strictly typed recovery plan:
- Transaction ID: {txn.get('txn_id')}
- Issuing Bank: {txn.get('bank')}
- Gateway Error Code: {txn.get('error_code')}
- Raw Gateway Description: {txn.get('error_desc')}
- Transaction Amount (INR): {txn.get('amount_inr')}
- Prior Attempt Count: {txn.get('retry_count', 1)}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RecoveryPlan.model_json_schema(),
                temperature=0.1
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {
            "root_cause": "Transient Network Gateway Degradation",
            "suggested_rail": "CARD",
            "delay_minutes": 0,
            "customer_message": "Network timeout encountered. Switching to card rail."
        }

def simulate_settlement_dispatch(plan: dict, txn: dict) -> dict:
    rail = plan["suggested_rail"]
    amount = float(txn.get("amount_inr", 0))
    
    if rail == "HALT":
        return {
            "dispatch_status": "EXECUTION_SUPPRESSED",
            "settlement_status": "UNRECOVERED",
            "settled_amount": 0.0,
            "idempotency_key": f"idemp_halt_{txn.get('txn_id')}"
        }
    
    benchmarks = {
        "CARD": 0.85,
        "NETBANKING": 0.78,
        "RETRY_SAME_RAIL": 0.75,
        "UPI": 0.72
    }
    prob = benchmarks.get(rail, 0.75)
    
    seed_val = sum(ord(c) for c in str(txn.get("txn_id", "default")))
    rng = random.Random(seed_val)
    settled = rng.random() <= prob

    return {
        "dispatch_status": "DISPATCHED_TO_ORCHESTRATOR",
        "settlement_status": "SETTLED" if settled else "SETTLEMENT_FAILED",
        "settled_amount": amount if settled else 0.0,
        "idempotency_key": f"idemp_{txn.get('txn_id')}_{rail.lower()}"
    }

def process_recovery(txn: dict) -> dict:
    error_code = str(txn.get("error_code", "")).upper()
    error_desc = str(txn.get("error_desc", "")).upper()
    amount = float(txn.get("amount_inr", 0))

    # Tier-1 Deterministic Fast-Path
    if error_code == "INSUFFICIENT_FUNDS":
        plan = {
            "root_cause": "Account Balance Deficit on Issuing Core Banking",
            "suggested_rail": "HALT",
            "delay_minutes": 0,
            "customer_message": "Transaction declined due to insufficient funds. Please use an alternate payment method."
        }
    elif error_code == "UPI_LIMIT_EXCEEDED":
        plan = {
            "root_cause": "NPCI Cumulative Daily UPI Velocity Exceeded",
            "suggested_rail": "CARD",
            "delay_minutes": 0,
            "customer_message": "Daily UPI transaction cap reached. Rerouted to Card payment."
        }
    elif error_code == "BANK_SERVER_DOWN":
        plan = {
            "root_cause": "Issuer CBS Unresponsive (504 Gateway Timeout)",
            "suggested_rail": "RETRY_SAME_RAIL",
            "delay_minutes": 0,
            "customer_message": "Issuer CBS down. Auto-retrying."
        }
    else:
        # Tier-2 LLM Escalation Route
        plan = call_gemini_recovery(txn)

    # FinTech Invariant Guardrails & Circuit Breakers
    circuit_breaker_triggered = False
    breaker_reason = "NONE"

    # Invariant 1: Enforce mandatory 15-minute backoff on 504 CBS downtime
    if ("504" in error_desc or "DOWN" in error_code or error_code == "BANK_SERVER_DOWN") and plan["suggested_rail"] != "HALT":
        if plan["delay_minutes"] < 15:
            plan["delay_minutes"] = 15
            circuit_breaker_triggered = True
            breaker_reason = "MANDATORY_CBS_504_BACKOFF"

    # Invariant 2: Block redundant VPA submissions on velocity cap
    elif ("LIMIT" in error_code or "VELOCITY" in error_desc) and plan["suggested_rail"] in ["UPI", "RETRY_SAME_RAIL"]:
        plan["suggested_rail"] = "CARD"
        circuit_breaker_triggered = True
        breaker_reason = "BLOCK_REDUNDANT_VPA_SUBMISSION"

    # Invariant 3: Block execution on zero ledger balance
    elif error_code == "INSUFFICIENT_FUNDS" and plan["suggested_rail"] != "HALT":
        plan["suggested_rail"] = "HALT"
        plan["delay_minutes"] = 0
        circuit_breaker_triggered = True
        breaker_reason = "HALT_INSUFFICIENT_BALANCE_RETRY"

    # Invariant 4: High-ticket value throttle (> INR 50k cannot auto-retry immediately)
    elif amount > 50000 and plan["suggested_rail"] == "RETRY_SAME_RAIL" and plan["delay_minutes"] < 30:
        plan["delay_minutes"] = 30
        circuit_breaker_triggered = True
        breaker_reason = "HIGH_VALUE_TRANSACTION_THROTTLE"

    dispatch_telemetry = simulate_settlement_dispatch(plan, txn)

    return {
        "txn_id": txn.get("txn_id"),
        "bank": txn.get("bank"),
        "amount_inr": amount,
        "error_code": error_code,
        "root_cause": plan["root_cause"],
        "suggested_rail": plan["suggested_rail"],
        "delay_minutes": plan["delay_minutes"],
        "circuit_breaker_triggered": circuit_breaker_triggered,
        "breaker_reason": breaker_reason,
        "dispatch_status": dispatch_telemetry["dispatch_status"],
        "settlement_status": dispatch_telemetry["settlement_status"],
        "settled_amount": dispatch_telemetry["settled_amount"],
        "idempotency_key": dispatch_telemetry["idempotency_key"],
        "customer_message": plan["customer_message"]
    }