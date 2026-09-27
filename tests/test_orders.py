import pytest
import sqlite3

def test_create_order_updates_db_and_stock(db_cursor, client):
  # 1. Create an inventory item through the API
  inv_res = client.post("/inventory", json={"name" : "Test Item", "quantity" : 10})
  assert inv_res.status_code == 200
  inv_id = inv_res.json()["id"]

  # 2. Place order via API
  order_res = client.post("/orders", json={"inventory_id" : inv_id, "quantity_ordered" : 7})
  assert order_res.status_code == 200
  order_id = order_res.json()["id"]

  db_cursor.execute("SELECT quantity FROM inventory WHERE id = ?", [inv_id])
  assert db_cursor.fetchone()[0] == 3

  #assert the stock decreased and an order row exists
  db_cursor.execute('SELECT id, quantity_ordered, inventory_id FROM "order" WHERE id = ?', [order_id])
  order_row = db_cursor.fetchone()
  assert order_row == (order_id, 7, inv_id)

#negative tests(insufficient-stock test)
#1. Insufficient stock (item has 5, order 10)
def test_create_order_insufficient_stock(db_cursor, client):

  #1. Insufficient stock
    inv_res = client.post("/inventory", json={"name" : "Test Item", "quantity" : 5})
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]

    # 2. Place order via API
    order_res = client.post("/orders", json={"inventory_id" : inv_id, "quantity_ordered" : 10})
    assert order_res.status_code == 409
    assert order_res.json()["detail"] == "Insufficient stock"

    db_cursor.execute('SELECT quantity FROM inventory WHERE id = ?', [inv_id])
    stock = db_cursor.fetchone()[0] #assert the stock is still 5
    assert stock == 5
    #"order" table has 0 rows.
    db_cursor.execute('SELECT COUNT(*) FROM "order"')
    order_count = db_cursor.fetchone()[0]
    assert order_count == 0

#2. Unknown item (inventory_id that doesn't exist)  ``Unknown item (inventory_id that doesn't exist): assert 404 and that no order row exists.
def test_create_order_unknown_item(db_cursor, client):

    order_res = client.post("/orders", json={"inventory_id" : 999, "quantity_ordered" : 10})
    assert order_res.status_code == 404
    assert order_res.json()["detail"] == "Item not found"

    db_cursor.execute('SELECT COUNT(*) FROM "order"')
    order_count = db_cursor.fetchone()[0]
    assert order_count == 0

def test_order_exactly_the_remaining_stock(db_cursor, client):
    inv_res = client.post("/inventory", json={"name" : "Test Item", "quantity" : 5})
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]

    order_res = client.post("/orders", json={"inventory_id" : inv_id, "quantity_ordered" : 5})
    assert order_res.status_code == 200
    db_cursor.execute("SELECT quantity FROM Inventory WHERE id=?", [inv_id])
    remaining_count = db_cursor.fetchone()[0]
    assert remaining_count == 0

def test_two_orders_in_sequence(db_cursor, client):

    inv_res = client.post("/inventory", json={"name" : "Test Item", "quantity" : 5})
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]

    order_res = client.post("/orders", json={"inventory_id" : inv_id, "quantity_ordered" : 3})
    assert order_res.status_code == 200
    db_cursor.execute("SELECT quantity FROM Inventory WHERE id=?", [inv_id])
    remaining_count = db_cursor.fetchone()[0]
    assert remaining_count == 2

    order_res = client.post("/orders", json={"inventory_id" : inv_id, "quantity_ordered" : 3})
    assert order_res.status_code == 409
    db_cursor.execute("SELECT quantity FROM Inventory WHERE id=?", [inv_id])
    remaining_count = db_cursor.fetchone()[0]
    assert remaining_count == 2

@pytest.mark.parametrize("invalid_quantity", [0, -3])
def test_create_order_zero_or_negative_quantity_returns_422(client, invalid_quantity):

    inv_res = client.post("/inventory", json={"name" : "Test Item", "quantity" : 5})
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]

    order_res = client.post("/orders", json={"inventory_id" : inv_id, "quantity_ordered" : invalid_quantity})
    assert order_res.status_code == 422
    assert order_res.json()["detail"][0]["msg"] == "Input should be greater than 0"
