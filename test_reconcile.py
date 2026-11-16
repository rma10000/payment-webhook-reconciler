import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from gateway_simulator import app, init_db
from reconcile import find_missing_webhooks

TEST_DB = "test_payments.db"

@pytest.fixture(autouse=True)
def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    app.state.db_path = TEST_DB
    app.state.fail_rate = 0.0
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

client = TestClient(app)

def test_webhook_processing_and_idempotency():
    payload = {
        "event_id": "evt_1001",
        "tx_id": "tx_9001",
        "amount": 125.50,
        "status": "CAPTURED"
    }

    res1 = client.post("/webhook", json=payload)
    assert res1.status_code == 200
    assert res1.json().get("status") == "processed"

    res2 = client.post("/webhook", json=payload)
    assert res2.status_code == 200
    assert res2.json().get("status") == "duplicate_ignored"

def test_reconciliation_detects_missing_webhooks():
    conn = sqlite3.connect(TEST_DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO gateway_ledger VALUES ('tx_001', 50.00, 'CAPTURED')")
    cur.execute("INSERT INTO gateway_ledger VALUES ('tx_002', 99.99, 'CAPTURED')")
    conn.commit()
    conn.close()

    client.post("/webhook", json={
        "event_id": "evt_001",
        "tx_id": "tx_001",
        "amount": 50.00,
        "status": "CAPTURED"
    })

    missing = find_missing_webhooks(TEST_DB)
    assert len(missing) == 1
    assert ('tx_002', 99.99, 'CAPTURED') in missing