import requests
import json
import time
from fastapi import HTTPException

def analyze_job_cv(job_description: str, resume_text: str):
    # Prompt mais limpo e eficiente
    user_message = f"""
        Vaga: {job_description}

        Currículo: {resume_text}

        Gere UM JSON com EXATAMENTE estas chaves: role, matched_requirements, missing_requirements, score, observation. 
        Os valores dentro dessas chaves devem ser em Português (PT-BR)
        """

    try:
        url = 'http://localhost:11434/api/chat'
        
        data = {
            "model": "recruiter-phi3",
            "messages": [
                {
                    "role": "system",
                    "content": "Analise a compatibilidade da vaga com o currículo e siga as regras do modelo."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "format": "json",
            "stream": False,
            "options": {
                "num_thread": 4
            }
        }
        
        start_time = time.time()
        
        # Use json= em vez de data= para serialização automática
        response = requests.post(
            url, 
            json=data,  # ✅ Corrigido: usa json= em vez de data=
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Tempo de resposta: {time.time() - start_time:.2f}s")
        print("Resposta bruta da API Ollama:", response.text)  # <-- Adicionado para debug

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erro Ollama: {response.text}"
            )
        
        res = response.json()
        content = res.get('message', {}).get('content', None)

        if content is None:
            raise HTTPException(
                status_code=500,
                detail="Resposta da API Ollama não contém campo 'content'"
            )

        # Se vier string, tenta fazer o parse
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                # Retorna a resposta bruta para análise
                raise HTTPException(
                    status_code=500, 
                    detail=f"Resposta não é JSON válido: {content}"
                )

        # Se vier dict vazio
        if not content:
            raise HTTPException(
                status_code=500,
                detail="Resposta da API Ollama veio vazia ({}). Reveja o prompt ou o Modelfile."
            )

        # Validação básica da estrutura
        required_keys = {"role","matched_requirements", "missing_requirements", 
                         "score", "observation"}
        if not isinstance(content, dict) or not all(key in content for key in required_keys):
            raise HTTPException(
                status_code=500,
                detail=f"JSON não contém todos os campos obrigatórios: {content}"
            )
        
        return content
    
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout da API Ollama")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama não disponível")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))