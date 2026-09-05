import pandas as pd

FAILURE_SCENARIOS = [
    {
        "bank": "HDFC",
        "error_code": "BANK_SERVER_DOWN",
        "error_desc": "Issuer Core Banking System (CBS) unresponsive via NPCI switch (HTTP 504)",
        "base_amount": 1850.0,
    },
    {
        "bank": "SBI",
        "error_code": "OTP_TIMEOUT",
        "error_desc": "Customer session expired. Two-factor authentication OTP not submitted within 180s",
        "base_amount": 420.0,
    },
    {
        "bank": "ICICI",
        "error_code": "INSUFFICIENT_FUNDS",
        "error_desc": "Transaction declined by issuer: account balance lower than debit amount",
        "base_amount": 9200.0,
    },
    {
        "bank": "AXIS",
        "error_code": "UPI_LIMIT_EXCEEDED",
        "error_desc": "Daily cumulative UPI transaction threshold of INR 100,000 reached for VPA",
        "base_amount": 34000.0,
    },
    {
        "bank": "KOTAK",
        "error_code": "CARD_SECURITY_BLOCKED",
        "error_desc": "Card transaction blocked due to international usage flag disabled by cardholder",
        "base_amount": 6500.0,
    },
]

def generate_test_batch(filename: str = "failed_transactions.csv", count: int = 50):
    records = []
    for i in range(count):
        archetype = FAILURE_SCENARIOS[i % len(FAILURE_SCENARIOS)]
        amount = archetype["base_amount"] + (i * 35.0)
        
        records.append({
            "txn_id": f"pay_live_test_{1000 + i}",
            "bank": archetype["bank"],
            "error_code": archetype["error_code"],
            "error_desc": archetype["error_desc"],
            "amount_inr": amount,
            "merchant_id": f"merch_{i % 5 + 1}"
        })
    
    df = pd.DataFrame(records)
    df.to_csv(filename, index=False)
    print(f"Generated {count} benchmark records saved to {filename}")

if __name__ == "__main__":
    generate_test_batch()