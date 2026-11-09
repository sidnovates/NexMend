from typing import Any, Dict, List
from app.models.schema import ManualChunk
from app.services.ingestion import get_embedding
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession


async def search_manual_chunks(
    session: AsyncSession,
    query_text: str,
    brand: str,
    model_series: str | None = None,
    limit: int = 3,
    min_similarity_threshold: float = 0.70,
) -> List[Dict[str, Any]]:

  """Strictly searches manual chunks grounded in manufacturer documentation.
  Guarantees zero brand cross-contamination and enforces a relevance quality
  floor.
  """
  clean_brand = brand.upper().strip()

 
  query_vector = get_embedding(query_text)

  # 2. Base query: Cosine distance calculation
  stmt = select(
      ManualChunk,
      ManualChunk.embedding.cosine_distance(query_vector).label("distance"),
  )


  conditions = [ManualChunk.brand == clean_brand]

  if model_series:
    clean_series = model_series.upper().strip()
    conditions.append(ManualChunk.model_series == clean_series)

  stmt = stmt.where(and_(*conditions))

  # 5. Rank by smallest distance (closest semantic match)
  stmt = stmt.order_by("distance").limit(limit)

  result = await session.execute(stmt)
  rows = result.all()

  # allback mechanism: If no chunks found for the specific model series,
  # search general manuals under the same brand (never a different brand).
  if not rows and model_series:
    fallback_stmt = (
        select(
            ManualChunk,
            ManualChunk.embedding.cosine_distance(query_vector).label(
                "distance"
            ),
        )
        .where(ManualChunk.brand == clean_brand)
        .order_by("distance")
        .limit(limit)
    )
    fallback_result = await session.execute(fallback_stmt)
    rows = fallback_result.all()

  # 7. Apply strict similarity threshold filtering
  matched_chunks = []
  for chunk, distance in rows:
    similarity = round(1.0 - float(distance), 4)

    # Reject chunks that do not meet the quality floor
    if similarity < min_similarity_threshold:
      continue

    matched_chunks.append({
        "id": chunk.id,
        "brand": chunk.brand,
        "model_series": chunk.model_series,
        "section_name": chunk.section_name,
        "content": chunk.content,
        "similarity_score": similarity,
    })

  return matched_chunks