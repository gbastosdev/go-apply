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

# ✅ CORREÇÃO: Baixa o modelo ESPECÍFICO do Modelfile (phi3:mini)
echo "Baixando modelo base phi3:mini..."
docker-compose exec ollama ollama pull phi3:mini

# ✅ CORREÇÃO: Remove modelos duplicados se existirem
docker-compose exec ollama ollama rm phi3 2>/dev/null || true
docker-compose exec ollama ollama rm phi3:latest 2>/dev/null || true

# Cria o modelo customizado
echo "Criando modelo recruiter-phi3..."
docker-compose exec ollama sh -c "pwd && ls -la /Modelfile && ollama create recruiter-phi3 -f /Modelfile"

# ✅ CORREÇÃO: Remove modelo duplicado se criou com tag errada
docker-compose exec ollama ollama rm recruiter-phi3:latest 2>/dev/null || true

echo "✅ Modelos disponíveis:"
docker-compose exec ollama ollama list

echo "🏃 Ollama rodando em http://localhost:11434"
docker-compose logs -f ollama