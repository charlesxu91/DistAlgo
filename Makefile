.PHONY: test compile smoke gpu-probe remote-gpu-smoke

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

remote-gpu-smoke:
	ssh charles@192.168.124.8 'bash -s' < scripts/remote_gpu_ray_smoke.sh
