#!/bin/bash

# 1. Inicia o container Ollama em segundo plano
docker-compose up -d

# 2. Aguarda o Ollama estar pronto (healthcheck)
echo "Aguardando Ollama iniciar..."
while ! curl -s http://localhost:11434 > /dev/null; do
    sleep 2
done

# 3. Baixa e executa o TinyLlama
echo "Baixando TinyLlama..."
docker-compose exec ollama ollama pull tinyllama

echo "TinyLlama está pronto!"