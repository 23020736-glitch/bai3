"""Goi LLM qua 9Router (API tuong thich OpenAI). Chi dung thu vien chuan."""
import json
import os
import urllib.request


def chat(messages, timeout=60):
    base = os.environ.get("NINEROUTER_BASE_URL", "http://localhost:20128/v1").rstrip("/")
    key = os.environ.get("NINEROUTER_API_KEY", "")
    model = os.environ.get("NINEROUTER_MODEL", "")
    if not model:
        raise RuntimeError("Hay dat NINEROUTER_MODEL (ten model/combo trong 9Router dashboard)")
    body = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode()
    req = urllib.request.Request(
        base + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]
