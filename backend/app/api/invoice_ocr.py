from fastapi import APIRouter, File, UploadFile

from app.api.upload_security import read_invoice_upload
from app.models.invoice_ocr import InvoiceOcrRequest
from app.services.invoice_ocr_service import missing_ocr_engine_response, recognize_invoice_text


router = APIRouter(prefix="/api/v1/invoice-ocr", tags=["invoice-ocr"])


@router.post("/recognize-text")
def recognize_text(request: InvoiceOcrRequest):
    return recognize_invoice_text(request)


@router.post("/upload")
async def upload_invoice_file(file: UploadFile = File(...)):
    content, is_text = await read_invoice_upload(file)
    filename = file.filename or ""
    if is_text:
        text = content.decode("utf-8", errors="ignore")
        return recognize_invoice_text(InvoiceOcrRequest(text=text))

    return missing_ocr_engine_response(filename)
