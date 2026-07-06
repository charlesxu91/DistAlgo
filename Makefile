.PHONY: test compile smoke

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
