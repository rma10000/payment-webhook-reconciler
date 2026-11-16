# Payment Webhook Reconciler

Working in production support for high-volume payment platforms, two issues come up constantly during peak traffic: merchant webhook endpoints timing out under load, and retry queues accidentally delivering the same event twice.

I put together this lightweight local simulator to test `event_id` idempotency keys, exponential backoff retries, and quick SQL reconciliation checks without needing access to an external sandbox.

## What's Inside

* `gateway_simulator.py` — Spins up a local SQLite database (`payments.db`), starts a FastAPI receiver (`/webhook`) that randomly throws HTTP 500 errors ~25% of the time, and fires 20 mock `CAPTURED` payments with retry logic and occasional duplicate payloads.
* `reconcile.py` — Compares `gateway_ledger` against `merchant_webhooks` using a SQL `LEFT JOIN` to catch any dropped transactions and writes the findings to `reconciliation_report.txt`.
* `test_reconcile.py` — Basic `pytest` coverage making sure duplicate `event_id` payloads get ignored and missing webhooks get flagged.

## Running It Locally

```bash
git clone https://github.com/rma10000/payment-webhook-reconciler.git
cd payment-webhook-reconciler

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

# Run the unit tests
python -m pytest -v

# Start the simulator (hit Ctrl+C once it finishes), then run the SQL audit
python gateway_simulator.py
python reconcile.py
```

### Alternative Quick Run (Windows PowerShell)

If you want to install dependencies, run the test suite, and launch the simulator in a single command without a virtual environment:

```powershell
python -m pip install -r requirements.txt; python -m pytest -v; python gateway_simulator.py
```

Once `"Simulation complete..."` appears, press **Ctrl + C** and run `python reconcile.py` to generate the audit report.

## Example Output

```text
[OK] Delivered tx_1c4f01b1 on attempt 1

Simulation complete. Press Ctrl+C to stop server, then run `python reconcile.py`.

=== Payment Reconciliation Report ===
Missing Merchant Webhooks Found: 0

Report saved to reconciliation_report.txt
Task complete
```

*(If a transaction fails all three delivery attempts, the script logs the missing `tx_id` and amount in GBP so it can be replayed.)*

## Notes & Next Steps

* **SQLite for portability:** I used SQLite so anyone cloning this repo can run it straight away with zero setup. In a real multi-worker environment, this would sit on PostgreSQL using `INSERT ... ON CONFLICT DO NOTHING` to handle concurrency properly.
* **Dead-letter queue:** Next thing I want to add is routing webhooks that fail all 3 retries into a separate `dlq_events` table with a replay script.



