#!/bin/bash

# Inicia o container
docker-compose up -d

# Aguarda o Ollama ficar pronto
echo "Aguardando Ollama iniciar..."
while ! curl -s http://localhost:11434 > /dev/null; do
    sleep 1
done

# Copia o Modelfile
echo "Copiando Modelfile para o container..."
docker cp "./Modelfile" $(docker-compose ps -q ollama):/Modelfile

# Baixa APENAS o modelo específico do Modelfile
echo "Baixando modelo base phi3..."
docker-compose exec ollama ollama pull phi3

# Cria o modelo customizado
echo "Criando modelo recruiter-phi3..."
docker-compose exec ollama sh -c "pwd && ls -la /Modelfile && ollama create recruiter-phi3 -f /Modelfile"

echo "✅ Modelos disponíveis:"
docker-compose exec ollama ollama list

echo "🏃 Ollama rodando em http://localhost:11434"
docker-compose logs -f ollama