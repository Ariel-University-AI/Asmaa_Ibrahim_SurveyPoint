import requests, base64, io, time
from PIL import Image

api_key = input("הכניסי API Key: ").strip()
HDR = {"x-goog-api-key": api_key}

# שלב 1 — בדוק מה זמין
print("\n=== בדיקת מודלים ===")
r = requests.get(
    "https://generativelanguage.googleapis.com/v1beta/models",
    headers=HDR, timeout=10)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    models = [m["name"] for m in r.json().get("models", [])
              if "generateContent" in m.get("supportedGenerationMethods", [])]
    print("מודלים זמינים:", models[:5])
else:
    print("שגיאה:", r.text[:200])

# שלב 2 — בדוק בקשת טקסט פשוטה
print("\n=== בדיקת טקסט ===")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
r2 = requests.post(URL, headers=HDR, json={"contents": [{"parts": [
    {"text": "Say OK"}
]}]}, timeout=15)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    print("תשובה:", r2.json()["candidates"][0]["content"]["parts"][0]["text"])
else:
    print("שגיאה:", r2.text[:300])
