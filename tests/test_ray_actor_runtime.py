import unittest

from distalgo.algorithms.graph.bfs import BFS
from distalgo.backends.ray_actor_runtime import RayActorRuntime


class FakeObjectRef:
    def __init__(self, value):
        self.value = value


class FakeRemoteMethod:
    def __init__(self, func):
        self.func = func

    def remote(self, *args, **kwargs):
        return FakeObjectRef(self.func(*args, **kwargs))


class FakeActorHandle:
    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, name):
        attr = getattr(self.obj, name)
        if callable(attr):
            return FakeRemoteMethod(attr)
        return attr


class FakeRemoteClass:
    def __init__(self, cls):
        self.cls = cls

    def remote(self, *args, **kwargs):
        return FakeActorHandle(self.cls(*args, **kwargs))


class FakeRay:
    def __init__(self):
        self.initialized = False
        self.remote_classes = []

    def init(self, **kwargs):
        self.initialized = True

    def remote(self, cls):
        self.remote_classes.append(cls.__name__)
        return FakeRemoteClass(cls)

    def get(self, refs):
        if isinstance(refs, list):
            return [ref.value for ref in refs]
        return refs.value


class RayActorRuntimeTest(unittest.TestCase):
    def test_ray_actor_runtime_partitions_graph_into_remote_workers(self):
        fake_ray = FakeRay()
        runtime = RayActorRuntime(ray_module=fake_ray)

        result = runtime.run(BFS(source=1), [(1, 2), (2, 3), (10, 11)], partitions=2)

        self.assertTrue(fake_ray.initialized)
        self.assertIn("PartitionWorker", fake_ray.remote_classes)
        self.assertEqual(result.output["distances"][3], 2)
        self.assertEqual(result.metrics["ray_actors"], 2.0)
        self.assertEqual(result.metrics["partitions"], 2.0)


if __name__ == "__main__":
    unittest.main()
