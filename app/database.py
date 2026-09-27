from fastapi import Depends
from sqlmodel import Session, create_engine, SQLModel
from app.models import Inventory, Order

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def create_inventory_orders():
    inventory = Inventory(name="Book", quantity=1)
    with Session(engine) as session:
        session.add(inventory)
        session.commit()

def main():
    create_db_and_tables()
    create_inventory_orders()

if __name__ == "__main__":
    main()
