"""Independent worker budgets; never acquire a budget around an async pipeline.

Pass a limiter directly to run_sync for one synchronous stage. Holding it while
awaiting another stage using the same limiter can deadlock. API/DB dependencies
continue to use AnyIO's separate default pool.
"""

import anyio

INGEST_LIMITER = anyio.CapacityLimiter(2)
VECTOR_LIMITER = anyio.CapacityLimiter(2)
EMBEDDING_RESULT_LIMITER = anyio.CapacityLimiter(1)
