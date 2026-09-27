from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session
from app.database import create_db_and_tables, get_session
from app.models import Inventory, Order, OrderCreate
from contextlib import asynccontextmanager



@asynccontextmanager
async def lifespan(app: FastAPI):
  create_db_and_tables()
  yield

app = FastAPI(lifespan=lifespan)

@app.post("/inventory/")
def create_item(item : Inventory, session:Session = Depends(get_session)):
  session.add(item)
  session.commit()
  session.refresh(item)
  return item

@app.post("/orders")
def create_order(order : OrderCreate, session:Session = Depends(get_session)):
  # 1. Look up the inventory row
  inventory = session.get(Inventory, order.inventory_id)
  if inventory is None:
    raise HTTPException(
      status_code=404, detail="Item not found"
      )
  if inventory.quantity < order.quantity_ordered:
    raise HTTPException(
      status_code=409, detail="Insufficient stock"
    )
  # 3. On success: subtract from quantity, save order, commit, refresh, and return

  inventory.quantity -= order.quantity_ordered
  db_order = Order(inventory_id=order.inventory_id, quantity_ordered=order.quantity_ordered)

  session.add(inventory)
  session.add(db_order)
  session.commit()
  session.refresh(db_order)

  return db_order
