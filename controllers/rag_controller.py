from http.client import HTTPException
import json
import requests

def analyze_job_cv(job_description, resume_text):
    # --- System + User messages ---
    system_message = """Você é um recrutador ATS especializado em triagem técnica. SEMPRE responda em PORTUGUÊS DO BRASIL (PT-BR).

                        Siga EXATAMENTE estes passos:

                        1. ANALISE a vaga:
                        - Requisitos técnicos (ex: Python, AWS)
                        - Experiência mínima (ex: 3 anos)
                        - Diferenciais (ex: inglês avançado)
                        - Modelo de trabalho (híbrido/remoto)

                        2. COMPARE com o currículo:
                        - [✔] Atendidos: liste os requisitos cumpridos
                        - [✖] Faltantes: cite apenas os que estão na vaga
                        - [★] Destaques: habilidades relevantes não pedidas

                        3. NOTA: dê uma nota de 0 a 100 (ex: "75/100").

                        Exemplo de resposta:
                        "Análise para vaga de Desenvolvedor Python:
                        [✔] Python (3 anos), Django
                        [✖] AWS, inglês intermediário
                        [★] Certificação em Docker
                        Nota: 70/100"
                        """

    user_message = f"Vaga:\n{job_description}\n\nCurrículo:\n{resume_text}"

    try:
        url = 'http://localhost:11434/api/chat'
        data = {
            "model": "openhermes", 
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