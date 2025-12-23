#!/bin/bash
docker run -d \
  --name bge-m3 \
  --network truffles_internal-net \
  --restart unless-stopped \
  -v bge-m3-data:/data \
  ghcr.io/huggingface/text-embeddings-inference:cpu-1.5 \
  --model-id BAAI/bge-m3
