from sqlmodel import SQLModel, Field
from typing import Optional

class RouteLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    origin: str
    destination: str
    geojson: str
