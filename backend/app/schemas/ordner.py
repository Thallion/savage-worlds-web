from datetime import datetime

from pydantic import BaseModel, Field


class OrdnerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class OrdnerUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class OrdnerResponse(BaseModel):
    id: int
    name: str
    erstellt_am: datetime
    anzahl_charaktere: int = 0

    model_config = {"from_attributes": True}
