from fastapi import HTTPException, status, Cookie, UploadFile, File, Form, FastAPI
from controllers import rag_controller
import pdfplumber
import re

router = FastAPI()

@router.post("/resume_file/")
async def upload_file_endpoint(cv: UploadFile = File(...), opportunity: str = Form(...)):
    """Process the opportunity and CV upload"""
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opportunity is required",
        )

    if cv.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    try:
        with pdfplumber.open(cv.file) as pdf:
            contents = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
        contents = re.sub(r'(?i)(experiência|experiencia|experience|formação|formacao|education|habilidades|skills|projetos|projects|certificações|certifications)',
        r'\n### \1\n',
        contents
        )
        # content_text = contents.decode('utf-8')
        response = rag_controller.analyze_job_cv(opportunity, contents)

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar arquivo: {str(e)}"
        )