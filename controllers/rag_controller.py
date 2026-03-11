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

    system_prompt = """You are an ATS (Applicant Tracking System) for analyzing compatibility between job postings and resumes.

        TASK:
        Compare the job requirements with the literal content of the resume and return a JSON analysis.

        LANGUAGE DETECTION:
        - Detect the language of the job description automatically.
        - Return ALL JSON values (matched_requirements, missing_requirements, observation) in the SAME language as the job description.
        - If job description is in Portuguese, respond in Portuguese.
        - If job description is in English, respond in English.
        - If job description is in Spanish, respond in Spanish.

        MATCHING RULES (follow strictly):
        - A requirement is MET only if the term, technology, or concept appears EXPLICITLY in the resume.
        - DO NOT make inferences. Example: "cloud experience" does NOT imply "AWS" if AWS is not written.
        - DO NOT use external knowledge. Analyze only the provided text.
        - If in doubt, classify as missing.

        SCORING RULES:
        - Calculate: (total matched_requirements / total job requirements) * 100
        - Round to integer.
        - Mandatory requirements count 2x in the calculation if explicitly marked as mandatory in the job posting.

        OUTPUT FORMAT:
        Return ONLY the JSON object below, with no text before or after, no markdown, no explanations:

        {"matched_requirements":["matched requirement 1","matched requirement 2"],"missing_requirements":["missing requirement 1"],"score":75,"observation":"objective observation about the candidate profile relative to the job posting"}"""
        
    user_message = f"""
        JOB DESCRIPTION:
        {job_description}
        
        RESUME:
        {resume_text}
        """

    try:
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,  # JSON de ATS nunca precisa de 5000 tokens
            temperature=0.1,
            system=system_prompt,
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