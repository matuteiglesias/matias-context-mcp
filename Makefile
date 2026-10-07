.PHONY: test check bootstrap-test smoke smoke-v02 smoke-v03 adoption-experiment knowledge-composition-proof

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

smoke-v03:
	PYTHONPATH=src python3 scripts/smoke_fixture.py --profile evidence-composition-v0.3 --output-dir artifacts/v03-evidence

adoption-experiment:
	PYTHONPATH=src python3 scripts/adoption_experiment.py --output artifacts/m6-adoption/report.json

knowledge-composition-proof:
	@test -n "$(KNOWLEDGE_INSPECT_ROOT)" || (echo "KNOWLEDGE_INSPECT_ROOT is required" >&2; exit 2)
	@test -n "$(KB_ARTIFACTS_ROOT)" || (echo "KB_ARTIFACTS_ROOT is required" >&2; exit 2)
	PYTHONPATH=src python3 scripts/m7_knowledge_composition_proof.py \
	  --knowledge-inspect-root "$(KNOWLEDGE_INSPECT_ROOT)" \
	  --kb-artifacts-root "$(KB_ARTIFACTS_ROOT)" \
	  --evidence-output artifacts/m7-knowledge-composition/report.json
