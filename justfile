IMAGE_TAG := "mikroseclist:latest"

# build docker image
build:
    docker build . -t {{ IMAGE_TAG }}

# run shell in container with .env
cli:
    docker run --rm -it --env-file .env -v .:/srv {{ IMAGE_TAG }} bash

# run locally
run:
    uv run python -m mikroseclist

# update dependencies
update:
    uv lock --upgrade && uv sync
