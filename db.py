import mysql.connector
from tkinter import messagebox


def get_connection():
    """Returns a fresh connection to the database."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="food_pos"
    )


# ================= CATEGORY MANAGEMENT ================= #

def fetch_categories():
    """Fetches list of category names (used for sidebar and dropdowns)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats
    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
        return []


def fetch_categories_full():
    """Fetches ID and Name for the management table."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY id DESC")
        data = cursor.fetchall()
        conn.close()
        return data
    except mysql.connector.Error as e:
        print(f"Error fetching full categories: {e}")
        return []


def save_category(name):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO categories (name) VALUES (%s)"
        cursor.execute(query, (name,))
        conn.commit()
        conn.close()
        return True
    except mysql.connector.Error as e:
        messagebox.showerror("DB Error", f"Could not save category: {e}")
        return False


def update_category_in_db(cat_id, new_name):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "UPDATE categories SET name = %s WHERE id = %s"
        cursor.execute(query, (new_name, cat_id))
        conn.commit()
        conn.close()
        return True
    except mysql.connector.Error as e:
        messagebox.showerror("DB Error", f"Could not update category: {e}")
        return False


def delete_category_from_db(cat_id):
    """Deletes all products associated with the category, then deletes the category."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        conn.start_transaction()

        # 1. Delete all products belonging to this category first
        cursor.execute("DELETE FROM products WHERE category_id = %s", (cat_id,))

        # 2. Delete the category
        cursor.execute("DELETE FROM categories WHERE id = %s", (cat_id,))

        conn.commit()
        return True
    except mysql.connector.Error as e:
        conn.rollback()
        messagebox.showerror("DB Error", f"Could not delete category and its products: {e}")
        return False
    finally:
        conn.close()


# ================= PRODUCT MANAGEMENT ================= #

def fetch_menu_from_db():
    """Used for the Home Page Grid (Cards)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            SELECT p.name, p.price, p.image_path, c.name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id
        """
        cursor.execute(query)
        menu_items = cursor.fetchall()
        conn.close()
        return menu_items
    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
        return []


def fetch_menu_full():
    """Used for the Add Items Page Table (Full details)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            SELECT p.id, p.name, c.name, p.price, p.image_path
            FROM products p
            JOIN categories c ON p.category_id = c.id
            ORDER BY p.id DESC
        """
        cursor.execute(query)
        data = cursor.fetchall()
        conn.close()
        return data
    except mysql.connector.Error as e:
        print(f"Error fetching menu full: {e}")
        return []


def save_product(name, category_name, price, image_path):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = %s", (category_name,))
        res = cursor.fetchone()
        if not res: return False
        cat_id = res[0]

        query = "INSERT INTO products (name, category_id, price, image_path) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (name, cat_id, price, image_path))
        conn.commit()
        conn.close()
        return True
    except mysql.connector.Error as e:
        messagebox.showerror("DB Error", f"Could not save product: {e}")
        return False


def update_product_in_db(p_id, name, category_name, price, image_path=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM categories WHERE name = %s", (category_name,))
        res = cursor.fetchone()
        if not res: return False
        cat_id = res[0]

        if image_path:
            query = "UPDATE products SET name=%s, category_id=%s, price=%s, image_path=%s WHERE id=%s"
            params = (name, cat_id, price, image_path, p_id)
        else:
            query = "UPDATE products SET name=%s, category_id=%s, price=%s WHERE id=%s"
            params = (name, cat_id, price, p_id)

        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except mysql.connector.Error as e:
        messagebox.showerror("DB Error", f"Could not update product: {e}")
        return False


def delete_product_from_db(product_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "DELETE FROM products WHERE id = %s"
        cursor.execute(query, (product_id,))
        conn.commit()
        conn.close()
        return True
    except mysql.connector.Error as e:
        messagebox.showerror("DB Error", f"Error deleting product: {e}")
        return False


# ================= ORDER MANAGEMENT ================= #

def save_order(cart_items, total_amount):
    if not cart_items:
        messagebox.showwarning("Empty Order", "Please add items to the cart first.")
        return False

    conn = get_connection()
    cursor = conn.cursor()
    try:
        conn.start_transaction()
        order_sql = "INSERT INTO orders (total_amount) VALUES (%s)"
        cursor.execute(order_sql, (total_amount,))
        order_id = cursor.lastrowid

        items_sql = """
            INSERT INTO order_items (order_id, product_name, quantity, price_per_unit, subtotal) 
            VALUES (%s, %s, %s, %s, %s)
        """
        for name, data in cart_items.items():
            qty = data['row'].qty
            price = data['row'].price
            subtotal = qty * price
            cursor.execute(items_sql, (order_id, name, qty, price, subtotal))

        conn.commit()
        messagebox.showinfo("Success", f"Order #{order_id} saved successfully!")
        return True
    except mysql.connector.Error as e:
        conn.rollback()
        messagebox.showerror("Error", f"Failed to save order: {e}")
        return False
    finally:
        conn.close()


def fetch_orders():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Changed JOIN to LEFT JOIN to ensure orders appear even if items were manually cleared
        query = """
            SELECT o.id, o.order_date, o.total_amount, 
                   GROUP_CONCAT(CONCAT(oi.product_name, ' (x', oi.quantity, ')') SEPARATOR ', ') as items
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id
            ORDER BY o.id DESC
        """
        cursor.execute(query)
        data = cursor.fetchall()
        conn.close()
        return data
    except mysql.connector.Error as e:
        print(f"Error fetching orders: {e}")
        return []


def delete_order_from_db(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        conn.start_transaction()
        cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
        cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
        conn.commit()
        return True
    except mysql.connector.Error as e:
        conn.rollback()
        messagebox.showerror("DB Error", f"Could not delete order history: {e}")
        return False
    finally:
        conn.close()