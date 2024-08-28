#!/bin/bash

# TODO Does not work in windows machines yet, will have to look into it
docker run --network host -d -e DEFAULT_REGION="eu-west-1" armdocker.rnd.ericsson.se/dockerhub-ericsson-remote/localstack/localstack:0.12.9
sleep 10
docker run --network host -it -v $(pwd):/usr/src/app armdocker.rnd.ericsson.se/proj-idun-aas/com.ericsson.oss.idunaas.python3:latest pytest -v --ignore=bob