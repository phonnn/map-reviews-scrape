#!/bin/bash
docker compose -f ./docker-compose.yml -p  map-reviews-web-1 up -d --build --remove-orphans
