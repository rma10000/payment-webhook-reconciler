import os
import sqlite3
import uuid
import random
import time
import threading
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="Merchant Webhook Receiver")
DB_PATH = "payments.db"
WEBHOOK_URL = "http://" + "127.0.0.1" + ":8000/webhook"

def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gateway_ledger (
            tx_id TEXT PRIMARY KEY,
            amount REAL,
            status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS merchant_webhooks (
            event_id TEXT PRIMARY KEY,
            tx_id TEXT,
            amount REAL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

@app.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()
    event_id = payload.get("event_id")
    tx_id = payload.get("tx_id")
    db_path = getattr(app.state, "db_path", DB_PATH)

    fail_rate = getattr(app.state, "fail_rate", 0.25)
    if random.random() < fail_rate:
        raise HTTPException(status_code=500, detail="Simulated Merchant Timeout")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM merchant_webhooks WHERE event_id = ?", (event_id,))
    if cur.fetchone():
        conn.close()
        return {"status": "duplicate_ignored", "event_id": event_id}

    cur.execute(
        "INSERT INTO merchant_webhooks (event_id, tx_id, amount, status) VALUES (?, ?, ?, ?)",
        (event_id, tx_id, payload.get("amount"), payload.get("status"))
    )
    conn.commit()
    conn.close()
    return {"status": "processed", "tx_id": tx_id}

def simulate_traffic(n_transactions=20):
    time.sleep(1.5)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for _ in range(n_transactions):
        tx_id = f"tx_{uuid.uuid4().hex[:8]}"
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        amount = round(random.uniform(10.0, 500.0), 2)

        cur.execute("INSERT INTO gateway_ledger VALUES (?, ?, ?)", (tx_id, amount, "CAPTURED"))
        conn.commit()

        payload = {"event_id": event_id, "tx_id": tx_id, "amount": amount, "status": "CAPTURED"}

        for attempt in range(3):
            try:
                res = requests.post(WEBHOOK_URL, json=payload, timeout=2)
                if res.status_code == 200:
                    print(f"[OK] Delivered {tx_id} on attempt {attempt + 1}")
                    if random.random() < 0.20:
                        dup = requests.post(WEBHOOK_URL, json=payload, timeout=2)
                        print(f"[DUP] Ignored duplicate webhook for {tx_id} -> {dup.json().get('status')}")
                    break
            except Exception:
                pass
            time.sleep(0.2 * (2 ** attempt))
        else:
            print(f"[FAILED] Dropped {tx_id} after 3 attempts!")

    conn.close()
    print("\nSimulation complete. Press Ctrl+C to stop server, then run `python reconcile.py`.")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    threading.Thread(target=simulate_traffic, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
