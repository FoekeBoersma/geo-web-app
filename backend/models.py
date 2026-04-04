from sqlmodel import SQLModel, Field
from typing import Optional

class RouteLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    origin: str
    destination: str
    geojson: str

class PointOfInterest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    latitute: float
    longitude: float
    name: Optional[str] = None
    description: Optional[str] = None
    picture_path: Optional[str] = None