from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.transaction import TransactionCreateRequest, TransactionUpdateRequest


def list_user_transactions(
    db: Session,
    user: User,
    transaction_type: TransactionType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Transaction]:
    query = db.query(Transaction).filter(
        Transaction.user_id == user.id,
        Transaction.deleted_at.is_(None),
    )
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)
    return (
        query.order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_transaction_or_404(db: Session, user: User, transaction_id: str) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if txn is None or txn.deleted_at is not None or txn.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return txn


def create_transaction(
    db: Session,
    user: User,
    payload: TransactionCreateRequest,
) -> Transaction:
    txn = Transaction(
        user_id=user.id,
        type=payload.type,
        category=payload.category,
        amount=payload.amount,
        description=payload.description,
        note=payload.note,
        date=payload.date,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def update_transaction(
    db: Session,
    user: User,
    transaction_id: str,
    payload: TransactionUpdateRequest,
) -> Transaction:
    txn = get_transaction_or_404(db, user, transaction_id)
    if payload.type is not None:
        txn.type = payload.type
    if payload.category is not None:
        txn.category = payload.category
    if payload.amount is not None:
        txn.amount = payload.amount
    if payload.description is not None:
        txn.description = payload.description
    if payload.note is not None:
        txn.note = payload.note
    if payload.date is not None:
        txn.date = payload.date
    db.commit()
    db.refresh(txn)
    return txn


def delete_transaction(db: Session, user: User, transaction_id: str) -> None:
    txn = get_transaction_or_404(db, user, transaction_id)
    txn.deleted_at = datetime.now(timezone.utc)
    db.commit()
