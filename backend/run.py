"""Dev entry point — `python run.py` from the backend folder.

Defaults to host=0.0.0.0 (so phones on the same WiFi can reach it). Override
via env vars HOST / PORT.
"""
import uvicorn

from app.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
