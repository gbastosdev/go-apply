#!/bin/bash

# 1. Inicia o container Ollama em segundo plano
docker-compose up -d

# 2. Aguarda o Ollama estar pronto (healthcheck)
echo "Aguardando Ollama iniciar..."
while ! curl -s http://localhost:11434 > /dev/null; do
    sleep 1
done

# 3. Baixa e executa o GPT Oss
echo "Baixando GPT Oss..."
docker-compose exec ollama ollama pull llama3:8b-instruct-q4_K_M

echo "GPT Oss está pronto!"