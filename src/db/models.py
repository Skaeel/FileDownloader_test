from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    content: Mapped[Optional[str]] = mapped_column(Text)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), server_default=func.timezone("UTC", func.now())
    )
    digit_counts: Mapped[Optional[dict]] = mapped_column(JSON)
