from __future__ import annotations

import importlib
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

Point = Tuple[float, ...]
Edge = Tuple[int, int]


@dataclass(frozen=True)
class KernelResult:
    output: Dict[str, object]
    metrics: Dict[str, float]
    backend: str
    device: str


def kmeans_kernel(
    data: Sequence[Point],
    k: int,
    max_iterations: int,
    tolerance: float,
    prefer_gpu: bool = True,
) -> KernelResult:
    points = [tuple(float(value) for value in point) for point in data]
    xp, backend, device = _array_backend(prefer_gpu)
    if xp is None:
        output, metrics = _kmeans_python(points, k, max_iterations, tolerance)
        return KernelResult(output=output, metrics=metrics, backend="python", device="cpu")

    array = xp.asarray(points, dtype=float)
    centers = array[:k].copy()
    assignments = xp.zeros((len(points),), dtype=int)
    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        distances = xp.sum((array[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        assignments = xp.argmin(distances, axis=1)
        next_centers = centers.copy()
        for cluster in range(k):
            mask = assignments == cluster
            if _scalar(xp.sum(mask)):
                next_centers[cluster] = xp.mean(array[mask], axis=0)
        shift = math.sqrt(_scalar(xp.sum((centers - next_centers) ** 2)))
        centers = next_centers
        iterations = iteration
        if tolerance > 0 and shift <= tolerance:
            converged = True
            break
    return KernelResult(
        output={
            "centers": [tuple(float(value) for value in row) for row in _to_list(centers)],
            "assignments": [int(value) for value in _to_list(assignments)],
        },
        metrics={
            "clusters": float(k),
            "points": float(len(points)),
            "iterations": float(iterations),
            "converged": 1.0 if converged else 0.0,
        },
        backend=backend,
        device=device,
    )


def pagerank_kernel(
    data: Sequence[Edge],
    damping: float,
    max_iterations: int,
    tolerance: float,
    prefer_gpu: bool = True,
) -> KernelResult:
    edges = [(int(src), int(dst)) for src, dst in data]
    nodes = sorted({node for edge in edges for node in edge})
    if not nodes:
        return KernelResult({"scores": {}}, {}, "python", "cpu")
    index = {node: offset for offset, node in enumerate(nodes)}
    n = len(nodes)
    xp, backend, device = _array_backend(prefer_gpu)
    if xp is None:
        output, metrics = _pagerank_python(edges, damping, max_iterations, tolerance)
        return KernelResult(output=output, metrics=metrics, backend="python", device="cpu")

    src_index = xp.asarray([index[src] for src, _ in edges], dtype=int)
    dst_index = xp.asarray([index[dst] for _, dst in edges], dtype=int)
    out_degree = xp.zeros((n,), dtype=float)
    for src in src_index:
        out_degree[int(_scalar(src))] += 1.0
    scores = xp.ones((n,), dtype=float) / float(n)
    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        next_scores = xp.ones((n,), dtype=float) * ((1.0 - damping) / float(n))
        dangling_mass = xp.sum(scores[out_degree == 0.0]) / float(n)
        next_scores += damping * dangling_mass
        contributions = scores[src_index] / out_degree[src_index]
        if hasattr(xp, "add") and hasattr(xp.add, "at"):
            xp.add.at(next_scores, dst_index, damping * contributions)
        else:
            for dst, contribution in zip(_to_list(dst_index), _to_list(contributions)):
                next_scores[int(dst)] += damping * float(contribution)
        delta = _scalar(xp.sum(xp.abs(next_scores - scores)))
        scores = next_scores
        iterations = iteration
        if delta <= tolerance:
            converged = True
            break
    total = _scalar(xp.sum(scores))
    if total:
        scores = scores / total
    return KernelResult(
        output={"scores": {node: float(_to_list(scores)[offset]) for node, offset in index.items()}},
        metrics={
            "active_vertices": float(n),
            "edges": float(len(edges)),
            "iterations": float(iterations),
            "converged": 1.0 if converged else 0.0,
        },
        backend=backend,
        device=device,
    )


def bfs_frontier_kernel(data: Sequence[Edge], source: int, prefer_gpu: bool = True) -> KernelResult:
    _, backend, device = _array_backend(prefer_gpu)
    adjacency: Dict[int, List[int]] = defaultdict(list)
    nodes = set()
    for src, dst in data:
        adjacency[int(src)].append(int(dst))
        adjacency[int(dst)].append(int(src))
        nodes.update((int(src), int(dst)))
    distances = {int(source): 0}
    queue = deque([int(source)])
    while queue:
        node = queue.popleft()
        for neighbor in sorted(adjacency[node]):
            if neighbor not in distances:
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)
    return KernelResult(
        output={"distances": distances},
        metrics={"active_vertices": float(len(nodes)), "max_depth": float(max(distances.values()) if distances else 0)},
        backend=backend,
        device=device,
    )


def _array_backend(prefer_gpu: bool):
    if prefer_gpu:
        try:
            cupy = importlib.import_module("cupy")
            if int(cupy.cuda.runtime.getDeviceCount()) > 0:
                return cupy, "cupy", "gpu"
        except Exception:
            pass
    try:
        return importlib.import_module("numpy"), "numpy", "cpu"
    except Exception:
        return None, "python", "cpu"


def _to_list(value):
    if hasattr(value, "get"):
        value = value.get()
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def _scalar(value) -> float:
    if hasattr(value, "item"):
        return float(value.item())
    if hasattr(value, "get"):
        return float(value.get())
    return float(value)


def _kmeans_python(points: Sequence[Point], k: int, max_iterations: int, tolerance: float):
    centers = list(points[:k])
    assignments = [0 for _ in points]
    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        assignments = [_nearest(point, centers) for point in points]
        next_centers = []
        for cluster in range(k):
            members = [point for point, assigned in zip(points, assignments) if assigned == cluster]
            if not members:
                next_centers.append(centers[cluster])
                continue
            dimensions = len(members[0])
            next_centers.append(tuple(sum(point[i] for point in members) / len(members) for i in range(dimensions)))
        shift = sum(_distance(left, right) for left, right in zip(centers, next_centers))
        centers = next_centers
        iterations = iteration
        if tolerance > 0 and shift <= tolerance:
            converged = True
            break
    return (
        {"centers": centers, "assignments": assignments},
        {"clusters": float(k), "points": float(len(points)), "iterations": float(iterations), "converged": float(converged)},
    )


def _pagerank_python(edges: Sequence[Edge], damping: float, max_iterations: int, tolerance: float):
    nodes = sorted({node for edge in edges for node in edge})
    outgoing: Dict[int, set[int]] = defaultdict(set)
    incoming: Dict[int, set[int]] = defaultdict(set)
    for src, dst in edges:
        outgoing[src].add(dst)
        incoming[dst].add(src)
        outgoing.setdefault(dst, set())
        incoming.setdefault(src, set())
    n = len(nodes)
    scores = {node: 1.0 / n for node in nodes}
    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        dangling_mass = sum(scores[node] for node in nodes if not outgoing[node]) / n
        next_scores = {}
        for node in nodes:
            rank = (1.0 - damping) / n
            rank += damping * dangling_mass
            rank += damping * sum(scores[src] / len(outgoing[src]) for src in incoming[node] if outgoing[src])
            next_scores[node] = rank
        delta = sum(abs(next_scores[node] - scores[node]) for node in nodes)
        scores = next_scores
        iterations = iteration
        if delta <= tolerance:
            converged = True
            break
    total = sum(scores.values())
    if total:
        scores = {node: value / total for node, value in scores.items()}
    return (
        {"scores": scores},
        {"active_vertices": float(n), "edges": float(len(edges)), "iterations": float(iterations), "converged": float(converged)},
    )


def _nearest(point: Point, centers: Sequence[Point]) -> int:
    distances = [_distance(point, center) for center in centers]
    return min(range(len(distances)), key=distances.__getitem__)


def _distance(left: Point, right: Point) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))
