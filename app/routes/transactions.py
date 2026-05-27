from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import requires_auth
from app.db.session import get_db
from app.models.transaction import TransactionType
from app.models.user import User
from app.schemas.response import ApiResponse, success_response
from app.schemas.transaction import (
    TransactionCreateRequest,
    TransactionPublic,
    TransactionUpdateRequest,
)
from app.services.transaction_service import (
    create_transaction,
    delete_transaction,
    get_transaction_or_404,
    list_user_transactions,
    update_transaction,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=ApiResponse[list[TransactionPublic]])
def list_transactions(
    type: TransactionType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(
        list_user_transactions(db, current_user, transaction_type=type, limit=limit, offset=offset)
    )


@router.post("", response_model=ApiResponse[TransactionPublic], status_code=201)
def create(
    payload: TransactionCreateRequest,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(create_transaction(db, current_user, payload))


@router.get("/{transaction_id}", response_model=ApiResponse[TransactionPublic])
def get_transaction(
    transaction_id: str,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(get_transaction_or_404(db, current_user, transaction_id))


@router.patch("/{transaction_id}", response_model=ApiResponse[TransactionPublic])
def update(
    transaction_id: str,
    payload: TransactionUpdateRequest,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(
        update_transaction(db, current_user, transaction_id, payload)
    )


@router.delete("/{transaction_id}", response_model=ApiResponse[None])
def delete(
    transaction_id: str,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    delete_transaction(db, current_user, transaction_id)
    return success_response()
