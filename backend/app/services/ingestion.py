import os
import pymupdf # PyMuPDF
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.schema import ManualChunk
from app.core.config import settings

# Setup embedding model based on available keys
def get_embedding(text: str) -> List[float]:
  """Generates vector embeddings for a given text string using Google Gemini."""
  if not settings.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not configured in .env")

  from langchain_google_genai import GoogleGenerativeAIEmbeddings

  # Use gemini-embedding-001 with 768 output dimensions
  embeddings = GoogleGenerativeAIEmbeddings(
      model="models/gemini-embedding-001",
      google_api_key=settings.GEMINI_API_KEY,
      output_dimensionality=768,
  )
  return embeddings.embed_query(text)


def extract_chunks_from_pdf(pdf_path: str, brand: str, model_series: str) -> List[Dict[str, Any]]:
    """
    Extracts text page by page from a service manual PDF and builds structured chunks.
    """
    doc = pymupdf.open(pdf_path)
    chunks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()

        if not text or len(text) < 50:
            continue  # Skip empty or spacer pages

        # Build a coherent section title or page marker
        section_name = f"Page {page_num + 1} - General Troubleshooting"
        first_line = text.split("\n")[0].strip()
        if len(first_line) < 80:
            section_name = f"Page {page_num + 1} - {first_line}"

        chunks.append({
            "brand": brand,
            "model_series": model_series,
            "section_name": section_name,
            "content": text
        })

    doc.close()
    return chunks


async def ingest_manual_to_db(
    session: AsyncSession, 
    pdf_path: str, 
    brand: str, 
    model_series: str
) -> int:
    """
    Parses a PDF manual, calculates vector embeddings for all chunks,
    and inserts them into the PostgreSQL manual_chunks table.
    """
    raw_chunks = extract_chunks_from_pdf(pdf_path, brand, model_series)
    saved_count = 0

    for item in raw_chunks:
        # Calculate vector embedding
        vector = get_embedding(item["content"])

        chunk_record = ManualChunk(
            brand=item["brand"],
            model_series=item["model_series"],
            section_name=item["section_name"],
            content=item["content"],
            embedding=vector
        )
        session.add(chunk_record)
        saved_count += 1

    await session.commit()
    return saved_count