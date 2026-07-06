# Cloud Native Distributed Algorithm Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MVP Python framework for cloud-native distributed graph and machine learning algorithms with pluggable execution models, local deterministic execution, Ray/GPU extension seams, checkpointing, and metrics.

**Architecture:** The MVP separates algorithm semantics from runtime orchestration. Algorithms declare an execution model such as graph message passing or aggregation; a local runtime executes partition workers deterministically for tests, while Ray and GPU modules provide capability seams for KubeRay and GPU-backed execution.

**Tech Stack:** Python standard library, optional Ray/CUDA/RAPIDS integration points, unittest-based tests.

---

### Task 1: Core Models and Runtime Tests

**Files:**
- Create: `tests/test_core_runtime.py`
- Create: `src/distalgo/core/models.py`
- Create: `src/distalgo/core/runtime.py`
- Create: `src/distalgo/core/checkpoint.py`
- Create: `src/distalgo/core/metrics.py`

- [x] **Step 1: Write failing tests**
  Cover algorithm specs, runtime checkpoint writes, metric collection, and result shape.

- [x] **Step 2: Run tests to verify failure**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: fail because `distalgo` package does not exist.

- [x] **Step 3: Implement minimal core**
  Add dataclasses for algorithm specs, checkpoint store, metrics registry, and local runtime.

- [x] **Step 4: Run tests to verify pass**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: core tests pass once algorithms are added.

### Task 2: Algorithm Plugin Tests

**Files:**
- Create: `tests/test_algorithms.py`
- Create: `src/distalgo/algorithms/base.py`
- Create: `src/distalgo/algorithms/graph/pagerank.py`
- Create: `src/distalgo/algorithms/graph/connected_components.py`
- Create: `src/distalgo/algorithms/graph/k_hop.py`
- Create: `src/distalgo/algorithms/ml/kmeans.py`

- [x] **Step 1: Write failing tests**
  Cover PageRank convergence, connected components, K-hop neighborhoods, and KMeans clustering.

- [x] **Step 2: Run tests to verify failure**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: fail because algorithms are missing.

- [x] **Step 3: Implement algorithms**
  Implement pure-Python deterministic versions that use the same plugin interface.

- [x] **Step 4: Run tests to verify pass**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: all algorithm tests pass.

### Task 3: Ray and GPU Extension Seams

**Files:**
- Create: `tests/test_capabilities.py`
- Create: `src/distalgo/backends/ray_backend.py`
- Create: `src/distalgo/backends/gpu.py`
- Create: `scripts/probe_gpu.py`

- [x] **Step 1: Write failing tests**
  Cover Ray resource specs, GPU probe fallback behavior, and multi-GPU virtualization boundary.

- [x] **Step 2: Run tests to verify failure**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: fail because backend modules are missing.

- [x] **Step 3: Implement capability modules**
  Add optional-import-safe Ray configuration helpers and GPU detection helpers.

- [x] **Step 4: Run tests to verify pass**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: all tests pass without Ray or CUDA installed.

### Task 4: Documentation

**Files:**
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/algorithms.md`
- Create: `docs/gpu-validation.md`

- [x] **Step 1: Document project positioning**
  Describe cloud-native distributed graph and ML algorithm execution framework.

- [x] **Step 2: Document algorithm families**
  Include graph ranking, traversal/connectivity, community detection, neighborhood/subgraph, graph features, clustering, regression/classification, and feature selection.

- [x] **Step 3: Document GPU validation**
  Explain single 5090 testing, logical multi-worker/fractional GPU testing, and why true multi-GPU/NCCL validation requires multiple physical GPUs.

- [x] **Step 4: Run final verification**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: all tests pass.

### Task 5: MVP Completion Closure

**Files:**
- Create: `tests/test_mvp_completion.py`
- Create: `distalgo/algorithms/graph/louvain.py`
- Create: `distalgo/algorithms/registry.py`
- Create: `distalgo/backends/ray_runtime.py`
- Create: `distalgo/cli.py`
- Create: `distalgo/core/job.py`
- Create: `distalgo/core/object_checkpoint.py`
- Create: `distalgo/core/prometheus.py`

- [x] **Step 1: Add failing MVP closure tests**
  Cover Louvain, JSON jobs, CLI, Ray adapter, object checkpointing, and metrics rendering.

- [x] **Step 2: Implement MVP closure modules**
  Add the community algorithm, job runner, CLI, Ray adapter boundary, object checkpoint store, and metrics server helper.

- [x] **Step 3: Run MVP closure tests**
  Run: `python3 -m unittest tests.test_mvp_completion -v`
  Expected: all MVP closure tests pass.
