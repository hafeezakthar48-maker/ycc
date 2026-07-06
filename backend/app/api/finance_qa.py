from fastapi import APIRouter

from app.models.finance_qa import FinanceQuestionRequest
from app.services.finance_qa_service import answer_finance_question


router = APIRouter(prefix="/api/v1/finance-qa", tags=["finance-qa"])


@router.post("/ask")
def ask_finance_question(request: FinanceQuestionRequest):
    return answer_finance_question(request)
