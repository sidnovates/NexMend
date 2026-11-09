import pytest
from app.core.database import AsyncSessionLocal
from app.models.schema import ManualChunk
from app.services.ingestion import get_embedding
from app.services.rag_service import search_manual_chunks


@pytest.mark.anyio
async def test_rag_pipeline():
    test_content = (
        "LG Front Load Error Code OE: Indicates water drainage failure. "
        "Steps to resolve: Check the drain hose for kinks or blockages. "
        "Unscrew and clean the drain pump filter located at the bottom front. "
        "If the drain pump hums without draining, physical pump replacement by a certified technician is required."
    )

    # 1. Test embedding generation
    embedding = get_embedding(test_content)
    assert len(embedding) == 768, f"Expected 768 dimensions, got {len(embedding)}"

    # 2. Seed a test chunk into PostgreSQL
    async with AsyncSessionLocal() as session:
        sample_chunk = ManualChunk(
            brand="LG",
            model_series="FHM1007",
            section_name="Drainage & OE Error Diagnostics",
            content=test_content,
            embedding=embedding,
        )
        session.add(sample_chunk)
        await session.commit()

        # 3. Test Retrieval
        query = "My machine is displaying OE and water is stuck inside the drum"
        results = await search_manual_chunks(
            session=session,
            query_text=query,
            brand="LG",
            model_series="FHM1007",
            limit=2,
            # min_similarity_threshold=0.60,
        )

        assert len(results) > 0, "Expected at least 1 relevant chunk"
        assert results[0]["brand"] == "LG"
        assert results[0]["similarity_score"] >= 0.60

        # 4. Test Cross-Brand Guardrail (SAMSUNG should return 0)
        samsung_results = await search_manual_chunks(
            session=session, query_text=query, brand="SAMSUNG", limit=2
        )
        assert len(samsung_results) == 0, (
            "Cross-brand guardrail failed: received results for SAMSUNG"
        )