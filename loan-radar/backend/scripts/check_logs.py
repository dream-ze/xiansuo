import httpx

resp = httpx.get("http://127.0.0.1:8080/api/crawler/logs", timeout=10)
data = resp.json()
logs = data.get("logs", [])
for l in logs:
    print(f"{l['timestamp']} [{l['level']}] {l['message']}")
