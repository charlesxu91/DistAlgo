# Contributing to DistAlgo

Thanks for considering a contribution. DistAlgo is intentionally small and
test-first: new behavior should come with a focused test and a clear note about
which runtime path it validates.

## Development

```bash
python3 -m pip install -e .
make test
make smoke
```

## Algorithm Contributions

When adding an algorithm:

- Add the implementation under `src/distalgo/algorithms/graph` or
  `src/distalgo/algorithms/ml`.
- Register it in `distalgo.algorithms.registry`.
- Mark its verification status explicitly.
- Add local correctness tests.
- Add partitioned or distributed-runtime tests before marking it
  `distributed_verified`.

## Verification Status

Use these status values:

- `distributed_verified`: tested through a framework runtime with more than one
  partition, actor, or Ray/KubeRay execution path.
- `local_verified`: tested for algorithm correctness, but not yet through a
  distributed runtime path.
- `planned`: documented target, not implemented.
