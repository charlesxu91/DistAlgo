# Algorithm Catalog

DistAlgo supports graph algorithms, graph mining, graph feature engineering, and
classic machine learning algorithms under one plugin contract.

## Verification Status Meaning

- `distributed_verified`: implemented and tested through a framework runtime
  with multiple partitions, Pregel-style execution, or Ray actor adapter
  coverage.
- `local_verified`: implemented and tested for algorithm correctness, but not
  yet through a distributed runtime path.
- `planned`: not implemented yet.

## Implemented and Distributed-Verified

| Family | Algorithm | Execution Model | Distributed Architecture | Verification |
| --- | --- | --- | --- | --- |
| Graph traversal | BFS | `graph_message` | BSP/Pregel, Actor seam | partitioned local + Ray actor adapter |
| Graph traversal | SSSP | `graph_message` | BSP/Pregel | Pregel runtime |
| Graph ranking | PageRank | `graph_message` | BSP/Pregel | partitioned local |
| Graph connectivity | Connected Components | `graph_message` | BSP/Pregel | partitioned local |
| Graph neighborhood | K-hop | `graph_message` | BSP/Pregel, Actor seam | partitioned local |
| Graph community | Louvain | `graph_message` | BSP/Pregel, Actor seam | partitioned local |
| Graph community | Label Propagation | `graph_message` | BSP/Pregel | partitioned local |
| Graph mining | K-core | `graph_message` | BSP/Pregel | partitioned local |
| Graph mining | Triangle Count | `map_reduce_shuffle` | Shuffle-style local seam | partitioned local |
| ML clustering | KMeans | `aggregation` | Master-worker / coordinator-worker | partitioned local |
| ML regression | Linear Regression | `aggregation` | Master-worker / coordinator-worker | partitioned local |

There are currently no implemented algorithms marked `local_verified` only. New
algorithms should not be marked `distributed_verified` until a distributed
runtime or partitioned-runtime test is added.

## Planned Graph Algorithms

Ranking:

- Personalized PageRank
- HITS

Traversal and connectivity:

- Strongly Connected Components
- All-pairs shortest path as a later target

Community detection and graph mining:

- Leiden
- Modularity
- HINLouvain for heterogeneous graphs
- LouvainX / attributed community discovery
- MAGI-style attributed pruning

Neighborhood and subgraph:

- Ego graph extraction
- Subgraph extraction
- Graph sampling
- Motif extraction

Similarity:

- Jaccard similarity
- Cosine similarity
- Common neighbors
- Adamic-Adar

Graph features:

- Degree features
- Centrality features
- Motif features
- Node2Vec / random-walk embeddings
- Community-derived features

## Planned Machine Learning Algorithms

Clustering:

- MiniBatch KMeans
- DBSCAN

Classification and regression:

- Logistic Regression
- SVM as an optional later target

Feature selection:

- Boruta
- Subgraph Boruta
- Mutual information
- Chi-square feature scoring

Dimensionality reduction:

- PCA
- SVD

Tree models:

- GBDT histogram training
- Random Forest as an optional later target

## Cross-Domain Graph ML Workflows

- Graph feature generation followed by ML classification.
- Attributed community detection.
- Community-aware feature selection.
- Subgraph mining followed by Boruta.
- K-hop neighborhood generation followed by embedding or clustering.

## Plugin Contract Direction

Every algorithm should declare:

- Algorithm family.
- Execution model.
- Input type and partition format.
- Communication pattern.
- State scope.
- Checkpoint cadence.
- CPU/GPU backend support.
- Required metrics.

This lets the runtime choose placement and orchestration without hard-coding
algorithm-specific behavior into Kubernetes, K3s, Ray, or KubeRay adapters.
