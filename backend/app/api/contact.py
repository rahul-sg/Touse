from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.contact_message import ContactMessage

router = APIRouter(tags=["contact"])
limiter = Limiter(key_func=get_remote_address)


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)


@router.post("/contact", status_code=201)
@limiter.limit("5/minute")
async def submit_contact(
    request: Request,
    body: ContactRequest,
    db: AsyncSession = Depends(get_db),
):
    """Store a message from the public contact form."""
    msg = ContactMessage(
        name=body.name.strip(),
        email=body.email,
        message=body.message.strip(),
    )
    db.add(msg)
    await db.commit()
    return {"status": "received"}
