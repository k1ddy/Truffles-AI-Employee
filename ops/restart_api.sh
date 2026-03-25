#!/bin/bash
docker stop truffles-api 2>/dev/null
docker rm truffles-api 2>/dev/null
cd /home/zhan/truffles-main/truffles-api
docker run -d --name truffles-api \
  --env-file .env \
  --network truffles_internal-net \
  --network proxy-net \
  -p 8000:8000 \
  --restart unless-stopped \
  -l traefik.enable=true \
  -l 'traefik.http.routers.truffles-api.rule=Host(`api.truffles.kz`)' \
  -l traefik.http.routers.truffles-api.entrypoints=websecure \
  -l traefik.http.routers.truffles-api.tls.certresolver=myresolver \
  -l traefik.http.services.truffles-api.loadbalancer.server.port=8000 \
  -l traefik.docker.network=proxy-net \
  truffles-api_truffles-api
