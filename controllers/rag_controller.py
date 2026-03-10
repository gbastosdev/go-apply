import os
from fastapi import HTTPException
from dotenv import load_dotenv
import json
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def extrair_json(texto):
    start = texto.find('{')
    end = texto.rfind('}')
    if start != -1 and end != -1 and end > start:
        return texto[start:end+1]
    return texto

def analyze_job_cv(job_description: str, resume_text: str):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="Internal error: Anthropic API key not configured."
        )

    system_message = """Você é um sistema ATS (Applicant Tracking System) de análise de compatibilidade entre vagas e currículos.

    TAREFA:
    Compare os requisitos da vaga com o conteúdo literal do currículo e retorne um JSON de análise.

    REGRAS DE MATCHING (siga rigorosamente):
    - Um requisito está ATENDIDO apenas se o termo, tecnologia ou conceito aparecer EXPLICITAMENTE no currículo.
    - NÃO faça inferências. Exemplo: "experiência com cloud" NÃO implica "AWS" se AWS não estiver escrito.
    - NÃO use conhecimento externo. Analise apenas o texto fornecido.
    - Se houver dúvida, classifique como missing.

    REGRAS DE SCORE:
    - Calcule: (total de matched_requirements / total de requisitos da vaga) * 100
    - Arredonde para inteiro.
    - Requisitos obrigatórios valem 2x na conta se estiverem explícitos na vaga como obrigatórios.

    IDIOMA: Todos os valores do JSON em português brasileiro.

    FORMATO DE SAÍDA:
    Retorne SOMENTE o objeto JSON abaixo, sem texto antes ou depois, sem markdown, sem explicações:

    {"matched_requirements":["requisito atendido 1","requisito atendido 2"],"missing_requirements":["requisito ausente 1"],"score":75,"observation":"observação objetiva sobre o perfil em relação à vaga"}"""

    user_message = f"""VAGA:
    {job_description}

    CURRÍCULO:
    {resume_text}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,  # JSON de ATS nunca precisa de 5000 tokens
            temperature=0.1,
            system=system_message,
            messages=[{"role": "user", "content": user_message}]
        )

        content_raw = message.content[0].text.strip()

        if not content_raw:
            raise HTTPException(
                status_code=502,
                detail="Unexpected response from external service."
            )

        try:
            content = json.loads(content_raw)
        except json.JSONDecodeError:
            json_puro = extrair_json(content_raw)
            try:
                content = json.loads(json_puro)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=502,
                    detail="External service response is not in valid format."
                )

        required_keys = {"matched_requirements", "missing_requirements", "score", "observation"}
        if not isinstance(content, dict) or not all(key in content for key in required_keys):
            raise HTTPException(
                status_code=502,
                detail="External service response does not contain all required fields."
            )

        return {"status": "success", "data": content}

    except HTTPException:
        raise
    except anthropic.APIStatusError:
        raise HTTPException(
            status_code=502,
            detail="Error when querying external service. Please try again later."
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal error while processing the analysis. Please try again later."
        )