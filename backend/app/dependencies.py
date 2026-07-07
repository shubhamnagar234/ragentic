from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
import uuid
from app.database import get_db
from app.config import settings
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        raw_user_id = payload.get("sub")
        if raw_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Convert raw string ID (like Google OAuth numeric ID) to deterministic UUID
        user_id = str(uuid.uuid5(uuid.NAMESPACE_OID, str(raw_user_id)))

        # Check if user exists — create if not
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Auto-create user on first login
            email = payload.get("email")
            if not email:
                email = f"{raw_user_id}@placeholder.local"
            
            user = User(
                id=user_id,
                email=email,
                name=payload.get("name", ""),
            )
            db.add(user)
            await db.commit()

        return user_id

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )