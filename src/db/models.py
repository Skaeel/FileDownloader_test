from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class File(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.timezone("UTC", func.now())
    )
    digit_counts: Mapped[dict]
