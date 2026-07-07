#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from distalgo.backends.gpu import GPUProbe


def main() -> int:
    probe = GPUProbe.from_system(os.environ)
    print(f"device_count={probe.device_count}")
    for index, name in enumerate(probe.device_names):
        print(f"device_{index}={name}")
    print(f"multi_gpu_mode={probe.multi_gpu_mode.value}")
    print(probe.virtualization_note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
