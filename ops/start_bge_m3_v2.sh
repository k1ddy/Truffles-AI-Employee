#!/bin/bash
docker run -d \
  --name bge-m3 \
  --network truffles_internal-net \
  --restart unless-stopped \
  -v bge-m3-data:/data \
  -e HF_HUB_OFFLINE=0 \
  ghcr.io/huggingface/text-embeddings-inference:cpu-1.2 \
  --model-id BAAI/bge-m3
