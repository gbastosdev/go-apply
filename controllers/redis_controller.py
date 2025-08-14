import datetime
from typing import Dict
from fastapi import HTTPException, status, UploadFile
import redis

class UploadController:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def handle_upload(
        self,
        session_id: str,
        opportunity: str,
        cv: UploadFile
    ) -> Dict[str, str]:
        """Processa o upload do CV e armazena no Redis"""
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID cookie is required",
            )

        if cv.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed",
            )

        try:
            contents = await cv.read()
            cv_key = f"{session_id}:cv"

            # Verifica se já existe o mesmo arquivo
            if self._is_duplicate_upload(session_id, cv_key, cv.filename, contents):
                return {"message": "CV já está salvo no Redis (mesmo arquivo)"}

            # Armazena os dados
            self._store_data(session_id, cv_key, opportunity, cv.filename, contents)

            return {"message": "CV e Opportunity armazenados com sucesso"}

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao processar arquivo: {str(e)}"
            )

    def _is_duplicate_upload(
        self,
        session_id: str,
        cv_key: str,
        filename: str,
        contents: bytes
    ) -> bool:
        """Verifica se é um upload duplicado"""
        existing_metadata = self.redis.hgetall(session_id)
        existing_cv = self.redis.get(cv_key) if self.redis.exists(cv_key) else None

        return (existing_metadata and 
                existing_cv and 
                existing_metadata.get(b'filename') == filename.encode() and 
                existing_cv == contents)

    def _store_data(
        self,
        session_id: str,
        cv_key: str,
        opportunity: str,
        filename: str,
        contents: bytes
    ) -> None:
        """Armazena os dados no Redis"""
        metadata = {
            "filename": filename,
            "opportunity": opportunity,
            "uploaded_at": datetime.datetime.now().isoformat()
        }

        self.redis.hset(session_id, mapping=metadata)
        self.redis.set(cv_key, contents)
        self.redis.expire(session_id, 1800)  # 30 minutos
        self.redis.expire(cv_key, 1800)      # 30 minutos