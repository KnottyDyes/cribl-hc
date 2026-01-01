.PHONY: review qa ci docs cleanup

AGENT_ENV=--env-file $$HOME/.config/ai-agent-lab/config.env
GIT_MOUNTS=-v "$$PWD":/work -v "$$PWD/.git":/work/.git -e GIT_DIR=/work/.git -e GIT_WORK_TREE=/work
GH_MOUNTS=-v $$HOME/.config/gh:/root/.config/gh:ro

review:
	docker run --rm $(AGENT_ENV) $(GIT_MOUNTS) review-agent:latest

qa:
	docker run --rm $(AGENT_ENV) $(GIT_MOUNTS) qa-agent:latest

ci:
	docker run --rm $(AGENT_ENV) $(GIT_MOUNTS) $(GH_MOUNTS) ci-agent:latest

docs:
	docker run --rm $(AGENT_ENV) $(GIT_MOUNTS) docs-agent:latest

cleanup:
	docker run --rm $(AGENT_ENV) $(GIT_MOUNTS) cleanup-agent:latest
