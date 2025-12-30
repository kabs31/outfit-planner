import requests

URL = "https://api.runpod.ai/v2/prxf4j6l1pd1j/run"
API_KEY = "dummy_key"

headers = {"Authorization": f"Bearer {API_KEY}"}

print("Testing with dummy key...")
resp = requests.post(URL, headers=headers, json={"input":{}})
print(f"Status: {resp.status_code}")
print(resp.text)
