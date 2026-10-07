.PHONY: test check smoke smoke-v02

test:
	python3 -m pytest -q

check:
	python3 -m compileall -q src scripts tests
	python3 -m pytest -q
	git diff --check
	@test -z "$$(git ls-files | grep -E '(^|/)(__pycache__/|.*\\.py[co]$$)' || true)"

smoke:
	PYTHONPATH=src python3 scripts/smoke_fixture.py --output-dir artifacts/mvp-evidence

smoke-v02:
	PYTHONPATH=src python3 scripts/smoke_fixture.py --profile estate-orientation-v0.2 --output-dir artifacts/v02-evidence
