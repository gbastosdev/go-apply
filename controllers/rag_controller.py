import os
from fastapi import HTTPException
from dotenv import load_dotenv
import json
import requests

load_dotenv()

def extrair_json(texto):
    start = texto.find('{')
    end = texto.rfind('}')
    if start != -1 and end != -1 and end > start:
        return texto[start:end+1]
    return texto  # fallback

def analyze_job_cv(job_description: str, resume_text: str):

    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

    if not perplexity_api_key:
        raise ValueError("A chave da API da Perplexity não foi encontrada.")

    system_message = """Você é um recrutador brasileiro especializado em ATS (Applicant Tracking System).

            REGRAS ABSOLUTAS:
            1. Analise estritamente o currículo e considere um requisito atendido SOMENTE se o termo exato, frase ou conceito estiver CLARAMENTE presente no texto do currículo.
            2. NÃO faça inferências, suposições, interpretações ou use conhecimento externo.
            3. Se a palavra ou requisito não estiver LITERALMENTE escrito no currículo, ele deve estar em 'missing_requirements'.
            4. TODOS os valores do JSON devem estar em PORTUGUÊS BRASILEIRO.
            5. Responda PRIMEIRO com seu raciocínio detalhado e DEPOIS com o JSON final.

            FORMATO DA RESPOSTA:
            [Seu raciocínio passo a passo aqui...]

            ```json
            {
                "matched_requirements": ["..."],
                "missing_requirements": ["..."],
                "score": 75,
                "observation": "..."
            }
            ```"""

    user_message = f"""
        VAGA PARA ANÁLISE:
        {job_description}

        CURRÍCULO PARA ANÁLISE:
        {resume_text}

        Siga as regras do system message e gere sua resposta no formato solicitado.
        """
    try:
        url = "https://api.perplexity.ai/chat/completions"

        data = {
            "model": "sonar-reasoning",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1,
            "max_tokens": 5000
        }

        headers = {
            "Authorization": f"Bearer {perplexity_api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=data, headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Erro Perplexity: {response.text}")

        res = response.json()
        content_raw = res.get('choices', [{}])[0].get('message', {}).get('content', None)

        if content_raw is None:
            raise HTTPException(status_code=500, detail="Resposta da API Perplexity não contém campo 'content'")

        json_puro = extrair_json(content_raw)

        try:
            content = json.loads(json_puro)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Resposta não é JSON válido!")

        # Validar estrutura básica do JSON
        required_keys = {"matched_requirements", "missing_requirements", "score", "observation"}
        if not isinstance(content, dict) or not all(key in content for key in required_keys):
            raise HTTPException(status_code=500, detail=f"JSON não contém todos os campos obrigatórios!")

        # Retorna conteúdo sem filtro adicional
        return content

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))