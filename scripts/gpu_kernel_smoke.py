#!/usr/bin/env python3
from __future__ import annotations

import json

from distalgo.backends.accelerated import bfs_frontier_kernel, kmeans_kernel, pagerank_kernel


def main() -> int:
    kmeans = kmeans_kernel(
        [(0.0, 0.0), (0.1, 0.0), (10.0, 10.0), (10.1, 10.0)],
        k=2,
        max_iterations=10,
        tolerance=1e-6,
        prefer_gpu=True,
    )
    pagerank = pagerank_kernel([(1, 2), (2, 3), (3, 1), (1, 3)], 0.85, 20, 1e-8, prefer_gpu=True)
    bfs = bfs_frontier_kernel([(1, 2), (2, 3), (1, 4)], source=1, prefer_gpu=True)
    payload = {
        "status": "passed",
        "kernels": {
            "kmeans": {"backend": kmeans.backend, "device": kmeans.device, "centers": kmeans.output["centers"]},
            "pagerank": {"backend": pagerank.backend, "device": pagerank.device, "score_count": len(pagerank.output["scores"])},
            "bfs": {"backend": bfs.backend, "device": bfs.device, "distances": bfs.output["distances"]},
        },
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
