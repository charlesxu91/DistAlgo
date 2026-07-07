.PHONY: test compile smoke gpu-probe gpu-kernel-smoke minio-smoke stress remote-gpu-smoke remote-minio-k3s-smoke remote-volcano-vgpu-preflight remote-volcano-vgpu-smoke

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

compile:
	PYTHONPYCACHEPREFIX=/private/tmp/distalgo-pycache python3 -m compileall src/distalgo scripts tests

smoke:
	PYTHONPATH=src python3 -m distalgo.cli list-algorithms --status
	PYTHONPATH=src python3 -m distalgo.cli run examples/pagerank_job.json --output /private/tmp/distalgo-pagerank-result.json
	PYTHONPATH=src python3 -m distalgo.cli run examples/sssp_job.json --output /private/tmp/distalgo-sssp-result.json
	PYTHONPATH=src python3 -m distalgo.cli benchmark
	PYTHONPATH=src python3 -m distalgo.cli report

gpu-probe:
	python3 scripts/probe_gpu.py

gpu-kernel-smoke:
	PYTHONPATH=src python3 scripts/gpu_kernel_smoke.py

minio-smoke:
	PYTHONPATH=src python3 scripts/minio_service_smoke.py

stress:
	PYTHONPATH=src python3 scripts/stress_benchmark.py --scale small --output /private/tmp/distalgo-stress.json

remote-gpu-smoke:
	ssh charles@192.168.124.8 'bash -s' < scripts/remote_gpu_ray_smoke.sh

remote-minio-k3s-smoke:
	ssh charles@192.168.124.8 'bash -s' < scripts/remote_minio_k3s_smoke.sh

remote-volcano-vgpu-preflight:
	ssh charles@192.168.124.8 'bash -s' < scripts/remote_volcano_vgpu_preflight.sh

remote-volcano-vgpu-smoke:
	ssh charles@192.168.124.8 'bash -s' < scripts/remote_volcano_vgpu_smoke.sh
