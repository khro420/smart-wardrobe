"""Isolated authentication microdiagnosis, not a user-response latency benchmark."""
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory(prefix="phase5f-auth-") as directory:
    os.environ.update(SMART_WARDROBE_DATA_DIR=directory,SMART_WARDROBE_DATABASE=str(Path(directory)/"test.db"),SMART_WARDROBE_TOKEN_SECRET="synthetic-auth-diagnostic-secret")
    from app.infrastructure.security import issue_access_token,token_user_id,hash_password,verify_password
    token=issue_access_token("synthetic-user")
    token_user_id(token)
    batches=[]
    for _ in range(10):
        start=perf_counter()
        for _ in range(10000):
            if token_user_id(token)!="synthetic-user": raise RuntimeError("Token validation failed.")
        batches.append((perf_counter()-start)/10000)
    encoded=hash_password("Synthetic-test-password-123")
    password=[]
    for _ in range(5):
        start=perf_counter()
        assert verify_password("Synthetic-test-password-123",encoded)
        password.append(perf_counter()-start)
    print(json.dumps({"token_seconds_per_call_batches":batches,"median_token_seconds":statistics.median(batches),"password_verify_seconds":password,"median_password_verify_seconds":statistics.median(password),"method":"Direct authentication function microdiagnosis only; no HTTP/DB/browser. No real credentials or tokens recorded."}))
