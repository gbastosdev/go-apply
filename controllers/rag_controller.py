from http.client import HTTPException
import json
import requests
import time

def analyze_job_cv(job_description, resume_text):
    # --- System + User messages ---
    sys_msg = """Você é um recrutador especialista em análise de compatibilidade entre vagas e currículos.
                Sua tarefa é comparar uma vaga com um currículo e retornar SEMPRE um JSON válido.
                TODOS os valores devem estar OBRIGATORIAMENTE em português - incluindo nomes de tecnologias, skills e observações.

                Regras obrigatórias:
                - O JSON deve seguir exatamente este formato:
                {
                "role": "string",
                "matched_requirements": ["string"],
                "missing_requirements": ["string"],
                "differentials": ["string"],
                "score": 0,
                "observation": "string"
                }

                - Só são permitidas exatamente estas chaves: role, matched_requirements, missing_requirements, differentials, score, observation.
                - Todos os campos são obrigatórios. Se não houver valor, use "" para strings, [] para listas e 0 para score.
                - Arrays devem ter no máximo 5 itens, sempre termos curtos e técnicos EM PORTUGUÊS (ex.: "Python", "Docker", "Rust", "Kubernetes", "Arquiteturas nativas da nuvem", "Sistemas distribuídos").
                - O campo score deve ser um número inteiro de 0 a 100 (sem aspas).
                - O campo observation deve ser escrito EM PORTUGUÊS, curto e técnico (ex.: "Lacuna em Rust e Go", "Experiência sólida em Python e tecnologias relacionadas"). Nunca deixe vazio.
                - IMPORTANTE: Mantenha nomes de tecnologias populares como estão (Python, Docker, Go, Rust, FastAPI, Kubernetes), mas traduza conceitos técnicos (ex.: "Database internals" → "Estruturas internas de banco de dados", "Cloud-native architectures" → "Arquiteturas nativas da nuvem").
                - Não escreva nada fora do JSON. Nenhum comentário, nenhum texto extra.
                - Nunca crie chaves diferentes das listadas.
                """
    user_message = f"""Vaga:
                        {job_description}

                        Currículo:
                        {resume_text}
                    """

    try:
        url = 'http://localhost:11434/api/chat'
        data = {
            "model": "llama3:8b-instruct-q4_K_M", 
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_message}
            ],
            "format": "json",
            "stream": False,
            "temperature": 0.0,
            "num_ctx": 2048,
            "num_threads": 4
        }
        data_to_send = json.dumps(data).encode('utf-8')
        start_time = time.time()
        response = requests.post(url, data=data_to_send)
        print(time.time() - start_time)
        res = response.json()
        content = res['message']['content']
        if isinstance(content, str):
            content = json.loads(content)
        return content
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))