import os

from fastapi import FastAPI

APP_VERSION = os.getenv("APP_VERSION", "0.0.0")

app = FastAPI(title="simple-url-shortener", version=APP_VERSION)


@app.get("/ping")
def ping() -> str:
    return "pong"
