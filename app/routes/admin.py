from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import requires_super_admin
from app.db.session import get_db
from app.models.budget import Budget
from app.models.chat import ChatMessage, ChatMessageRole, ChatMessageStatus, ChatSession
from app.models.email import Email
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction, TransactionType
from app.models.user import User, UserStatus
from app.models.verification_code import VerificationCode
from app.schemas.admin import AnalyticsResponse, EmailPublic, VerificationCodePublic
from app.schemas.chat import AdminChatSessionPublic, ChatSessionWithMessages
from app.schemas.finance import AdminFinanceAnalyticsResponse
from app.schemas.response import ApiResponse, success_response
from app.services.chat_service import get_chat_session_or_404, list_all_chat_sessions

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(requires_super_admin)],
)


@router.get("/emails", response_model=ApiResponse[list[EmailPublic]])
def list_emails(db: Session = Depends(get_db)):
    emails = (
        db.query(Email)
        .filter(Email.deleted_at.is_(None))
        .order_by(Email.created_at.desc())
        .all()
    )
    return success_response(emails)


@router.get("/emails/{email_id}", response_model=ApiResponse[EmailPublic])
def get_email(email_id: str, db: Session = Depends(get_db)):
    email = db.get(Email, email_id)
    if email is None or email.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    return success_response(email)


@router.get(
    "/verification-codes",
    response_model=ApiResponse[list[VerificationCodePublic]],
)
def list_verification_codes(db: Session = Depends(get_db)):
    verification_codes = (
        db.query(VerificationCode)
        .filter(VerificationCode.deleted_at.is_(None))
        .order_by(VerificationCode.created_at.desc())
        .all()
    )
    return success_response(verification_codes)


@router.get(
    "/verification-codes/{verification_code_id}",
    response_model=ApiResponse[VerificationCodePublic],
)
def get_verification_code(verification_code_id: str, db: Session = Depends(get_db)):
    verification_code = db.get(VerificationCode, verification_code_id)
    if verification_code is None or verification_code.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification code not found",
        )
    return success_response(verification_code)


@router.get("/chats", response_model=ApiResponse[list[AdminChatSessionPublic]])
def list_chats(db: Session = Depends(get_db)):
    return success_response(list_all_chat_sessions(db))


@router.get("/chats/{session_id}", response_model=ApiResponse[ChatSessionWithMessages])
def get_chat(session_id: str, db: Session = Depends(get_db)):
    return success_response(get_chat_session_or_404(db, session_id))


@router.get("/analytics", response_model=ApiResponse[AnalyticsResponse])
def get_analytics(db: Session = Depends(get_db)):
    total_chat_sessions = (
        db.query(ChatSession).filter(ChatSession.deleted_at.is_(None)).count()
    )
    total_messages = (
        db.query(ChatMessage).filter(ChatMessage.deleted_at.is_(None)).count()
    )
    active_users = (
        db.query(User)
        .filter(
            User.status == UserStatus.ACTIVE,
            User.deleted_at.is_(None),
        )
        .count()
    )
    failed_ai_calls = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.role == ChatMessageRole.ASSISTANT,
            ChatMessage.status == ChatMessageStatus.FAILED,
            ChatMessage.deleted_at.is_(None),
        )
        .count()
    )
    total_transactions = (
        db.query(Transaction).filter(Transaction.deleted_at.is_(None)).count()
    )
    total_budgets = db.query(Budget).filter(Budget.deleted_at.is_(None)).count()
    total_savings_goals = (
        db.query(SavingsGoal).filter(SavingsGoal.deleted_at.is_(None)).count()
    )
    return success_response(
        AnalyticsResponse(
            total_chat_sessions=total_chat_sessions,
            total_messages=total_messages,
            active_users=active_users,
            failed_ai_calls=failed_ai_calls,
            total_transactions=total_transactions,
            total_budgets=total_budgets,
            total_savings_goals=total_savings_goals,
        )
    )


@router.get("/finance-analytics", response_model=ApiResponse[AdminFinanceAnalyticsResponse])
def get_finance_analytics(db: Session = Depends(get_db)):
    """Platform-wide financial aggregates across all users."""
    from decimal import Decimal
    from sqlalchemy import func

    total_users = (
        db.query(User)
        .filter(User.deleted_at.is_(None))
        .count()
    )
    total_transactions = (
        db.query(Transaction).filter(Transaction.deleted_at.is_(None)).count()
    )
    total_income = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.type == TransactionType.INCOME,
            Transaction.deleted_at.is_(None),
        )
        .scalar()
    ) or Decimal("0")
    total_expenses = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.type == TransactionType.EXPENSE,
            Transaction.deleted_at.is_(None),
        )
        .scalar()
    ) or Decimal("0")
    total_budgets = db.query(Budget).filter(Budget.deleted_at.is_(None)).count()
    total_savings_goals = (
        db.query(SavingsGoal).filter(SavingsGoal.deleted_at.is_(None)).count()
    )
    return success_response(
        AdminFinanceAnalyticsResponse(
            total_users=total_users,
            total_transactions=total_transactions,
            total_income_logged=Decimal(str(total_income)),
            total_expenses_logged=Decimal(str(total_expenses)),
            total_budgets=total_budgets,
            total_savings_goals=total_savings_goals,
        )
    )
