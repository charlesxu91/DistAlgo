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
    def __init__(self, cls, options=None):
        self.cls = cls
        self.options = options or {}

    def remote(self, *args, **kwargs):
        return FakeActorHandle(self.cls(*args, **kwargs))


class FakeRay:
    def __init__(self):
        self.initialized = False
        self.remote_classes = []
        self.remote_options = []

    def init(self, **kwargs):
        self.initialized = True

    def remote(self, cls=None, **options):
        if cls is None:
            def decorator(actual_cls):
                self.remote_classes.append(actual_cls.__name__)
                self.remote_options.append(options)
                return FakeRemoteClass(actual_cls, options)

            return decorator
        self.remote_classes.append(cls.__name__)
        self.remote_options.append(options)
        return FakeRemoteClass(cls, options)

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
        self.assertEqual(result.metrics["ray_actor_gpus"], 0.0)

    def test_ray_actor_runtime_can_request_fractional_gpu_per_actor(self):
        fake_ray = FakeRay()
        runtime = RayActorRuntime(ray_module=fake_ray, num_gpus_per_actor=0.25)

        result = runtime.run(BFS(source=1), [(1, 2), (2, 3), (10, 11)], partitions=2)

        self.assertIn({"num_gpus": 0.25}, fake_ray.remote_options)
        self.assertEqual(result.metrics["ray_actor_gpus"], 0.25)


if __name__ == "__main__":
    unittest.main()
