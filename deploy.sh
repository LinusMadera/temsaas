#!/bin/bash

git pull

docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

docker image prune -f 