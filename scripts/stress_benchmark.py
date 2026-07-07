#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from distalgo.algorithms.graph.pagerank import PageRank
from distalgo.algorithms.graph.sssp import SSSP
from distalgo.algorithms.ml.kmeans import KMeans
from distalgo.core.runtime import LocalRuntime


SCALES = {
    "small": {"nodes": 128, "points": 256, "dimensions": 4},
    "medium": {"nodes": 1024, "points": 2048, "dimensions": 8},
    "large": {"nodes": 4096, "points": 8192, "dimensions": 8},
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic DistAlgo stress benchmarks.")
    parser.add_argument("--scale", choices=sorted(SCALES), default="small")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    config = SCALES[args.scale]
    graph = _graph(config["nodes"])
    points = _points(config["points"], config["dimensions"])
    runtime = LocalRuntime.in_memory()

    cases = [
        ("pagerank", PageRank(max_iterations=20, tolerance=1e-7), graph, 8),
        ("sssp", SSSP(source=0, max_iterations=config["nodes"]), [(src, dst, 1.0) for src, dst in graph], 8),
        ("kmeans", KMeans(k=4, max_iterations=25, tolerance=1e-5), points, 8),
    ]
    results = []
    started = perf_counter()
    for name, algorithm, data, partitions in cases:
        case_started = perf_counter()
        result = runtime.run(algorithm, data, partitions=partitions)
        elapsed_ms = (perf_counter() - case_started) * 1000.0
        results.append(
            {
                "algorithm": name,
                "iterations": result.iterations,
                "converged": result.converged,
                "elapsed_ms": elapsed_ms,
                "metrics": result.metrics,
            }
        )
    payload = {
        "status": "passed",
        "scale": args.scale,
        "total_elapsed_ms": (perf_counter() - started) * 1000.0,
        "results": results,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def _graph(nodes: int):
    edges = []
    for node in range(nodes):
        edges.append((node, (node + 1) % nodes))
        edges.append((node, (node * 7 + 3) % nodes))
    return edges


def _points(count: int, dimensions: int):
    points = []
    for index in range(count):
        cluster = index % 4
        base = float(cluster * 10)
        points.append(tuple(base + ((index * (dim + 3)) % 17) / 100.0 for dim in range(dimensions)))
    return points


if __name__ == "__main__":
    raise SystemExit(main())
