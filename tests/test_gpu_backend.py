import unittest

from distalgo.backends.gpu_backend import DeviceBackend, choose_backend, gpu_capability_report
from distalgo.backends.gpu import GPUProbe, MultiGpuMode


class GPUBackendTest(unittest.TestCase):
    def test_choose_backend_falls_back_to_cpu_when_no_gpu_visible(self):
        backend = choose_backend(GPUProbe.from_environment(env={}), preferred="auto")

        self.assertEqual(backend.device, "cpu")
        self.assertEqual(backend.library, "python")

    def test_choose_backend_selects_single_gpu_when_visible(self):
        backend = choose_backend(GPUProbe(device_names=["NVIDIA GeForce RTX 5090"], env={}), preferred="gpu")

        self.assertEqual(backend.device, "gpu")
        self.assertEqual(backend.library, "rapids-compatible")

    def test_gpu_capability_report_explains_single_card_limit(self):
        report = gpu_capability_report(GPUProbe(device_names=["NVIDIA GeForce RTX 5090"], env={}))

        self.assertEqual(report["multi_gpu_mode"], MultiGpuMode.LOGICAL_ONLY.value)
        self.assertFalse(report["true_multi_gpu_validation"])


if __name__ == "__main__":
    unittest.main()
