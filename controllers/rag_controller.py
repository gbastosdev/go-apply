from http.client import HTTPException
import json
import requests
import time

def analyze_job_cv(job_description, resume_text):
    # --- System + User messages ---
    sys_msg = """Você é um avaliador de compatibilidade entre vagas de emprego e currículos.
                Sua saída deve ser SEMPRE um JSON válido em PT-BR.
                Regras obrigatórias:
                - Somente estas chaves são permitidas: role, matched_requirements, missing_requirements, differentials, compatibility_score, observation.
                - Todos os campos são obrigatórios. Se não houver valor, use "" para strings, [] para listas e 0 para nota.
                - Cada array deve ter no MÁXIMO 5 itens.
                - A compatibility_score deve ser um número inteiro de 0 a 100 (sem aspas).
                - Não escreva nada fora do JSON. Nenhum comentário, nenhum texto extra.
                - Nunca invente novas chaves.
                Sua função é preencher esse JSON de forma fiel com base na vaga e no currículo
                """
    user_message = f"""Analise a vaga e o currículo abaixo e retorne o JSON no formato exato especificado.

                        Formato esperado:
                        {{
                        "role": "string",
                        "matched_requirements": ["string"],
                        "missing_requirements": ["string"],
                        "differentials": ["string"],
                        "compatibility_score": 0,
                        "observation": "string"
                        }}

                        Exemplo de preenchimento:
                        {{
                        "role": "Analista de Dados",
                        "matched_requirements": ["SQL", "Python"],
                        "missing_requirements": ["Power BI"],
                        "differentials": ["Certificação Google Analytics"],
                        "compatibility_score": 75,
                        "observation": "Falta experiência em ferramentas de BI"
                        }}

                        Agora aplique o mesmo formato para os dados abaixo.

                        Vaga:
                        {job_description}

                        Currículo:
                        {resume_text}
                    """

    try:
        url = 'http://localhost:11434/api/chat'
        data = {
            "model": "dolphin-phi", 
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_message}
            ],
            "format": "json",
            "stream": False,
            "temperature": 0.1,
            "num_ctx": 512,
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