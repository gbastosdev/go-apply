from http.client import HTTPException
import json
import requests

def analyze_job_cv(job_description, resume_text):
    # --- System + User messages ---
    system_message = """Você é um recrutador sênior especializado em triagem de currículos utilizando sistemas ATS (Applicant Tracking System). 
                    Sua função é ler uma vaga e um currículo, identificar todos os requisitos da vaga e compará-los com o perfil do candidato.
                    Sua análise deve ser objetiva, técnica e livre de invenções.

                    Siga as regras:
                    1. Leia atentamente a vaga e extraia:
                    - Tecnologias e ferramentas exigidas
                    - Nível de experiência para cada requisito
                    - Competências diferenciais (desejáveis)
                    - Soft skills e idiomas solicitados
                    - Localização e formato de trabalho

                    2. Compare com o currículo:
                    - Aponte quais requisitos são atendidos
                    - Liste lacunas relevantes
                    - Destaque pontos fortes do candidato

                    3. Sempre responda no formato JSON válido:
                    {
                    "match_percent": <número entre 0 e 100>,
                    "strengths": ["..."],
                    "gaps": ["..."],
                    "summary": "Resumo de até 3 frases sobre compatibilidade"
                    }

                    4. Não inclua informações que não estejam presentes na vaga ou no currículo.
                    """

    user_message = f"Vaga:\n{job_description}\n\nCurrículo:\n{resume_text}"

    try:
        url = 'http://localhost:11434/api/chat'
        data = {
            "model": "mistral:instruct",  # ou tinyllama se estiver testando
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "stream": False,
            "temperature": 0.1
        }
        data_to_send = json.dumps(data).encode('utf-8')
        response = requests.post(url, data=data_to_send)
        res = response.json()
        return {"response": res['message']['content']}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))