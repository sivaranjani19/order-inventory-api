from typing import Optional, List

from sqlmodel import Field, SQLModel, Relationship

class Inventory(SQLModel, table=True):
  id: int | None = Field(default=None, primary_key=True)
  name: str
  quantity: int
  orders: List[Order] = Relationship(back_populates="inventory")


class Order(SQLModel, table=True):
  id: Optional[int] = Field(default=None, primary_key=True)
  quantity_ordered : int = Field(gt=0)

  inventory_id : int = Field(default=None, foreign_key="inventory.id")
  inventory: Inventory = Relationship(back_populates="orders")

class OrderCreate(SQLModel):
    inventory_id: int
    quantity_ordered: int = Field(gt=0)

