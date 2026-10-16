"""Measure one API process's peak RSS, optionally including real ONNX inference.

Run from backend/: python scripts/check_memory.py --max-mib 300
Use --embed for the first-request footprint (requires the model cache).
"""

import argparse
import asyncio
import json
import resource
import sys
from pathlib import Path


async def measure(embed: bool) -> dict:
    import uvicorn

    from main import app

    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=0, workers=1,
        proxy_headers=False, log_level="warning",
    ))
    task = asyncio.create_task(server.serve())
    try:
        async with asyncio.timeout(120):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("API server exited before startup completed")
                await asyncio.sleep(0.05)
        if embed:
            from app.core.embedding_runtime import SharedEmbeddings

            vectors = await SharedEmbeddings().aembed_documents([
                "RAGFUSION retrieves passages from tenant-authorized sources.",
                "ONNX Runtime generates MiniLM embeddings on the CPU.",
            ])
            assert len(vectors) == 2 and all(len(vector) == 384 for vector in vectors)
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mib = peak / (1024 * 1024 if sys.platform == "darwin" else 1024)
        forbidden = sorted(set(sys.modules) & {
            "torch", "torchvision", "sentence_transformers", "transformers", "FlagEmbedding",
        })
        return {"phase": "startup+embedding" if embed else "startup", "peak_rss_mib": round(mib, 2),
                "platform": sys.platform, "forbidden_imports": forbidden}
    finally:
        server.should_exit = True
        await task


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embed", action="store_true")
    parser.add_argument("--max-mib", type=float, default=300)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    result = asyncio.run(measure(args.embed))
    print(json.dumps(result))
    if result["forbidden_imports"] or result["peak_rss_mib"] > args.max_mib:
        raise SystemExit(1)
