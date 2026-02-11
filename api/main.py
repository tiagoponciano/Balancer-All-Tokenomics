"""
FastAPI backend: streams full tokenomics data from NEON so the Streamlit app
can run on a memory-constrained host (e.g. Streamlit Cloud) by requesting
data from this API instead of loading directly from NEON.

Run: uvicorn api.main:app --host 0.0.0.0 --port 8000
Set DATABASE_URL and NEON_TABLE in env (or .env in project root).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import pandas as pd
import io

app = FastAPI(title="Balancer Tokenomics API", version="1.0.0")

TABLE = os.getenv("NEON_TABLE", "tokenomics").strip() or "tokenomics"


def get_engine():
    from sqlalchemy import create_engine
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL not set")
    if "sslmode" not in url:
        url = url.rstrip("/") + ("&" if "?" in url else "?") + "sslmode=require"
    return create_engine(url)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/data/stream")
def stream_data():
    """
    Stream the full tokenomics table as CSV in chunks. Use when the client has
    enough memory to hold the result (e.g. Streamlit on Railway/Render with 2GB+ RAM).
    """
    engine = get_engine()
    chunk_size = 20_000
    offset = 0
    first = True

    def generate():
        nonlocal offset, first
        while True:
            sql = f'SELECT * FROM "{TABLE}" ORDER BY block_date LIMIT {chunk_size} OFFSET {offset}'
            df = pd.read_sql(sql, engine)
            if df.empty:
                break
            buf = io.StringIO()
            df.to_csv(buf, index=False, header=first)
            buf.seek(0)
            yield buf.read()
            first = False
            offset += chunk_size
            if len(df) < chunk_size:
                break

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tokenomics.csv"},
    )


@app.get("/data/chunk")
def get_chunk(offset: int = 0, limit: int = 50_000):
    """
    Return one chunk of the table as JSON. Client can call repeatedly and
    concatenate (e.g. in Streamlit with enough memory).
    """
    engine = get_engine()
    sql = f'SELECT * FROM "{TABLE}" ORDER BY block_date LIMIT {limit} OFFSET {offset}'
    df = pd.read_sql(sql, engine)
    # Convert dates for JSON
    if "block_date" in df.columns:
        df["block_date"] = df["block_date"].astype(str)
    return df.to_dict(orient="records")
