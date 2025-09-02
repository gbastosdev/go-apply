import os
from dotenv import load_dotenv
from fastapi import HTTPException
import json
import requests

load_dotenv()

# Carregar a chave da API da Perplexity
perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

if not perplexity_api_key:
    raise ValueError("A chave da API da Perplexity não foi encontrada.")

def analyze_job_cv(job_description: str, resume_text: str):
    user_message = f"""
        Vaga: {job_description}
        Currículo: {resume_text}

        Você é um recrutador especializado em ATS.
        Analise o currículo estritamente e **somente** considere um requisito atendido se o termo exato, frase ou conceito estiver claramente presente no texto do currículo.
        Não faça nenhuma inferência, suposição, interpretação ou preenchimento com conhecimento externo.
        Se a palavra ou requisito não estiver literalmente escrito no currículo, ele deve estar em 'missing_requirements'.

        Além disso:
        - Considere que o candidato é graduado se encontrar expressões literais como "formado em", "bacharelado em" ou similares no texto, mesmo em seções corridas.
        - Calcule e informe a experiência somando os períodos indicados nas experiências, considerando somente frontend/mobile, e valide se é maior que 3 anos.

        Responda **somente em JSON válido completo**, sem nenhum comentário ou texto extra.
        Use o formato exato:

        {{
            "role": "Cargo pretendido a partir da vaga",
            "matched_requirements": ["Requisito explicitamente presente no currículo"],
            "missing_requirements": ["Requisito não explicitamente presente no currículo"],
            "score": número inteiro de 0 a 100 representando compatibilidade,
            "observation": "Resumo em português ressaltando pontos fortes e fracos, graduação explicita e cálculo de experiência baseado somente no texto fornecido"
        }}

        - Não adicione campos extras.
        - Use português (PT-BR).
        """



    try:
        # Definir o endpoint da API da Perplexity
        url = "https://api.perplexity.ai/chat/completions"

        # Definir os dados da requisição
        data = {
            "model": "sonar",  # Modelo de exemplo, pode ser ajustado conforme necessário
            "messages": [
                {"role": "system", "content": "Analise a compatibilidade da vaga com o currículo e siga as regras do modelo."},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.2,
            "max_tokens": 5000
        }

        # Cabeçalhos da requisição
        headers = {
            "Authorization": f"Bearer {perplexity_api_key}",
            "Content-Type": "application/json"
        }

        # Enviar a requisição POST para a API da Perplexity
        response = requests.post(url, json=data, headers=headers)

        # Verificar o status da resposta
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Erro Perplexity: {response.text}")

        # Processar a resposta
        res = response.json()
        content = res.get('choices', [{}])[0].get('message', {}).get('content', None)

        if content is None:
            raise HTTPException(status_code=500, detail="Resposta da API Perplexity não contém campo 'content'")

        # Tentar fazer o parse do conteúdo como JSON
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Resposta não é JSON válido: {content}")

        # Validar a estrutura do JSON
        required_keys = {"role", "matched_requirements", "missing_requirements", "score", "observation"}
        if not isinstance(content, dict) or not all(key in content for key in required_keys):
            raise HTTPException(status_code=500, detail=f"JSON não contém todos os campos obrigatórios: {content}")

        return content

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

