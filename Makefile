export HI_VERSION = $(shell cat HI_VERSION)

NOW_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')

.SECONDARY:

docker-build:	Dockerfile
	docker build \
		--label "name=hi" \
		--label "version=$(HI_VERSION)" \
		--label "build-date=$(NOW_DATE)" \
		--tag hi:$(HI_VERSION) .

docker-run:	Dockerfile flutter-webapp-build
	./run_container.sh

docker-stop:	
	docker stop hi
