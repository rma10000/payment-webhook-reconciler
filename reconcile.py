import sqlite3

def find_missing_webhooks(db_path="payments.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    query = """
    SELECT g.tx_id, g.amount, g.status
    FROM gateway_ledger g
    LEFT JOIN merchant_webhooks m ON g.tx_id = m.tx_id
    WHERE m.tx_id IS NULL
    """
    missing = cur.execute(query).fetchall()
    conn.close()
    return missing

def export_report(missing, output_file="reconciliation_report.txt"):
    lines = [
        "=== Payment Reconciliation Report ===",
        f"Missing Merchant Webhooks Found: {len(missing)}"
    ]
    for tx_id, amount, status in missing:
        lines.append(f" - Unreconciled Transaction: {tx_id} | £{amount:.2f} | {status}")

    report_text = "\n".join(lines) + "\n"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text.strip())
    print(f"\nReport saved to {output_file}")
    print("Task complete")

if __name__ == "__main__":
    missing = find_missing_webhooks()
    export_report(missing)
