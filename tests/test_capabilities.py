import os
import subprocess
import sys
import unittest

from distalgo.backends.gpu import GPUProbe, MultiGpuMode
from distalgo.backends.ray_backend import RayResourcePlan


class CapabilityTest(unittest.TestCase):
    def test_ray_resource_plan_serializes_cpu_gpu_requirements(self):
        plan = RayResourcePlan(cpus=4, gpus=1, memory_mb=8192)

        self.assertEqual(plan.to_ray_options(), {"num_cpus": 4, "num_gpus": 1})
        self.assertEqual(plan.to_kubernetes_limits()["nvidia.com/gpu"], "1")

    def test_gpu_probe_handles_missing_cuda_without_import_failure(self):
        probe = GPUProbe.from_environment(env={})

        self.assertEqual(probe.device_count, 0)
        self.assertFalse(probe.has_cuda)
        self.assertEqual(probe.multi_gpu_mode, MultiGpuMode.UNAVAILABLE)

    def test_single_gpu_can_only_do_logical_multi_worker_not_true_multi_gpu(self):
        probe = GPUProbe(device_names=["NVIDIA GeForce RTX 5090"], env={"CUDA_VISIBLE_DEVICES": "0"})

        self.assertEqual(probe.device_count, 1)
        self.assertEqual(probe.multi_gpu_mode, MultiGpuMode.LOGICAL_ONLY)
        self.assertIn("fractional GPU", probe.virtualization_note)

    def test_probe_script_runs_from_repository_root(self):
        completed = subprocess.run(
            [sys.executable, "scripts/probe_gpu.py"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("device_count=", completed.stdout)


if __name__ == "__main__":
    unittest.main()
