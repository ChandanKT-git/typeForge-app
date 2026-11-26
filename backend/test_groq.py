import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(".env")
client = Groq()

try:
    resp = client.chat.completions.create(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": "hi"}],
        max_completion_tokens=10
    )
    print("SUCCESS with max_completion_tokens")
except Exception as e:
    print("FAIL 1:", e)

try:
    resp = client.chat.completions.create(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10
    )
    print("SUCCESS with max_tokens")
except Exception as e:
    print("FAIL 2:", e)

try:
    resp = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10
    )
    print("SUCCESS with llama3-70b-8192 and max_tokens")
except Exception as e:
    print("FAIL 3:", e)

