export HI_VERSION = $(shell cat HI_VERSION)

NOW_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')

.SECONDARY:

docker-build:	Dockerfile
	docker build \
		--label "name=hi" \
		--label "version=$(HI_VERSION)" \
		--label "build-date=$(NOW_DATE)" \
		--tag hi:$(HI_VERSION) .

docker-run:	.private/env/local.sh Dockerfile
	./run_container.sh

docker-stop:	
	docker stop hi

local-env:	.private/env/local.sh
	./packaging/env-generate.py

