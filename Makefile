export HI_VERSION = $(shell cat HI_VERSION)

NOW_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')

.SECONDARY:

docker-build:	Dockerfile
	docker build \
		--label "name=hi" \
		--label "version=$(HI_VERSION)" \
		--label "build-date=$(NOW_DATE)" \
		--tag hi:$(HI_VERSION) \
		--tag hi:latest .

docker-run:	.private/env/local.dev Dockerfile
	./deploy/run_container.sh -bg

docker-run-fg:	.private/env/local.dev Dockerfile
	./deploy/run_container.sh

docker-stop:	
	docker stop hi

env-build:	.private/env/local.dev
	./deploy/env-generate.py -env-name local

env-build-dev:	.private/env/development.dev
	./deploy/env-generate.py --env-name development

.private/env/local.dev:


.private/env/development.dev:
