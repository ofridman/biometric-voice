"""Database connection and operations for speaker embeddings using pgvector."""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Create a new database connection."""
    conn = psycopg2.connect(
        host=os.environ["DATABASE_HOST"],
        port=os.environ.get("DATABASE_PORT", "5432"),
        user=os.environ["DATABASE_USER"],
        password=os.environ["DATABASE_PASSWORD"],
        dbname=os.environ.get("DATABASE_NAME", "biometric_voice"),
    )
    register_vector(conn)
    return conn


def upsert_speaker(name: str, embedding: list[float]) -> None:
    """Insert or update a speaker's embedding."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            emb = np.array(embedding, dtype=np.float32)
            cur.execute(
                """
                INSERT INTO speakers (name, embedding, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (name) DO UPDATE
                SET embedding = EXCLUDED.embedding, updated_at = NOW()
                """,
                (name, emb),
            )
        conn.commit()
    finally:
        conn.close()


def get_embedding(name: str) -> Optional[list[float]]:
    """Retrieve a speaker's embedding by name."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT embedding FROM speakers WHERE name = %s", (name,))
            row = cur.fetchone()
            if row is None:
                return None
            return list(row[0])
    finally:
        conn.close()


def get_all_embeddings() -> dict[str, list[float]]:
    """Return all enrolled speakers and their embeddings."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, embedding FROM speakers")
            return {row[0]: list(row[1]) for row in cur.fetchall()}
    finally:
        conn.close()


def list_speakers() -> list[str]:
    """Return all enrolled speaker names."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM speakers ORDER BY name")
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def remove_speaker(name: str) -> bool:
    """Remove a speaker. Returns True if a row was deleted."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM speakers WHERE name = %s", (name,))
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def speaker_exists(name: str) -> bool:
    """Check if a speaker is enrolled."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM speakers WHERE name = %s", (name,))
            return cur.fetchone() is not None
    finally:
        conn.close()
