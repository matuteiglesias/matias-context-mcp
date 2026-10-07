.PHONY: test check bootstrap-test smoke smoke-v02 adoption-experiment

test:
	python3 -m pytest -q

bootstrap-test:
	python3 -m pytest -q tests/test_bootstrap_cli.py

check:
	python3 -m compileall -q src scripts tests
	python3 -m pytest -q
	git diff --check
	@test -z "$$(git ls-files | grep -E '(^|/)(__pycache__/|.*\\.py[co]$$)' || true)"

smoke:
	PYTHONPATH=src python3 scripts/smoke_fixture.py --output-dir artifacts/mvp-evidence

smoke-v02:
	PYTHONPATH=src python3 scripts/smoke_fixture.py --profile estate-orientation-v0.2 --output-dir artifacts/v02-evidence

adoption-experiment:
	PYTHONPATH=src python3 scripts/adoption_experiment.py --output artifacts/m6-adoption/report.json
