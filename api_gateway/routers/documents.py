# api_gateway/routers/documents.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File, Form
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from services.document_service import DocumentService
from dependencies import get_document_service

router = APIRouter()

class DocumentBase(BaseModel):
    title: str
    description: Optional[str] = None
    customer_id: Optional[str] = None
    tags: Optional[List[str]] = None

class DocumentResponse(DocumentBase):
    id: str
    file_url: str
    file_type: str
    created_at: str
    size: int

    class Config:
        from_attributes = True

@router.post("/documents/upload", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    submission_id: str = Form(...),
    customer_id: Optional[str] = Form(None),
    category: str = Form("files"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Загрузка нового документа
    """
    try:
        result = await document_service.upload_document(
            submission_id=submission_id,
            file=file,
            category=category
        )

        return {
            "status": "success",
            "message": "Документ успешно загружен",
            "file_info": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке документа: {str(e)}")

@router.get("/documents/{submission_id}/{filename}", response_model=Dict[str, Any])
async def get_document(
    submission_id: str = Path(..., title="ID запроса"),
    filename: str = Path(..., title="Имя файла"),
    category: str = Query("files", title="Категория файла"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Получение конкретного документа
    """
    try:
        document = document_service.get_document(
            submission_id=submission_id,
            filename=filename,
            category=category
        )

        return document
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении документа: {str(e)}")

@router.get("/customers/{customer_id}/documents", response_model=List[Dict[str, Any]])
async def get_customer_documents(
    customer_id: str = Path(..., title="ID клиента"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Получение документов клиента
    """
    try:
        documents = document_service.get_customer_documents(customer_id)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении документов: {str(e)}")

@router.delete("/documents/{submission_id}/{filename}", response_model=Dict[str, Any])
async def delete_document(
    submission_id: str = Path(..., title="ID запроса"),
    filename: str = Path(..., title="Имя файла"),
    category: str = Query("files", title="Категория файла"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Удаление документа
    """
    try:
        result = document_service.delete_document(
            submission_id=submission_id,
            filename=filename,
            category=category
        )

        if not result:
            raise HTTPException(status_code=404, detail="Документ не найден")

        return {
            "status": "success",
            "message": "Документ успешно удален"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении документа: {str(e)}")

@router.get("/documents/search", response_model=Dict[str, Any])
async def search_documents(
    query: str = Query(..., title="Поисковый запрос"),
    customer_id: Optional[str] = Query(None, title="ID клиента для ограничения поиска"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Поиск по документам
    """
    try:
        results = document_service.search_documents(query, customer_id)
        return {
            "query": query,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске документов: {str(e)}")