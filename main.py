import os
import shutil
from tkinter import messagebox, ttk, filedialog
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps

# Import database functions
from db import (fetch_categories, fetch_menu_from_db, save_order, delete_product_from_db,
                save_category, delete_category_from_db, update_category_in_db,
                save_product, update_product_in_db, fetch_orders, delete_order_from_db,
                fetch_categories_full, fetch_menu_full)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Food POS System")
app.geometry("1200x700")
app.iconbitmap("assets/pos.ico")

# ================= STATE MANAGEMENT ================= #
current_category = "All"
food_cards = []
cart_items = {}
selected_image_path = None
selected_cat_id = None
selected_product_id = None
selected_view_order_id = None

# ================= NAVIGATION LOGIC ================= #
def show_page(page_name):
    home_page.grid_forget()
    add_cat_page.grid_forget()
    add_item_page.grid_forget()
    view_orders_page.grid_forget()

    if page_name == "home":
        home_page.grid(row=0, column=0, sticky="nsew")
        refresh_products_grid()
    elif page_name == "cat":
        add_cat_page.grid(row=0, column=0, sticky="nsew")
        refresh_cat_table()
    elif page_name == "item":
        add_item_page.grid(row=0, column=0, sticky="nsew")
        refresh_item_table()
        update_item_cat_dropdown()
    elif page_name == "orders":
        view_orders_page.grid(row=0, column=0, sticky="nsew")
        refresh_orders_table()

# ================= ROOT GRID ================= #
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

# ================= LEFT SIDEBAR ================= #
category_frame = ctk.CTkFrame(app, width=180, corner_radius=0)
category_frame.grid(row=0, column=0, sticky="nsw", padx=5, pady=5)
category_frame.grid_propagate(False)

def filter_category(category):
    global current_category
    current_category = category
    show_page("home")
    update_grid()

def refresh_sidebar():
    for widget in category_frame.winfo_children():
        widget.destroy()
    ctk.CTkLabel(category_frame, text="Categories", font=("Arial", 18, "bold")).pack(pady=15)
    ctk.CTkButton(category_frame, text="All", height=40, fg_color="#555",
                  command=lambda: filter_category("All")).pack(fill="x", padx=15, pady=6)

    for cat in fetch_categories():
        ctk.CTkButton(category_frame, text=cat, height=40,
                      command=lambda c=cat: filter_category(c)).pack(fill="x", padx=15, pady=6)

# ================= MIDDLE PANEL CONTAINER ================= #
middle_panel_container = ctk.CTkFrame(app, fg_color="transparent")
middle_panel_container.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
middle_panel_container.grid_rowconfigure(1, weight=1)
middle_panel_container.grid_columnconfigure(0, weight=1)

# --- GLOBAL NAVIGATION BAR ---
nav_bar = ctk.CTkFrame(middle_panel_container)
nav_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))

ctk.CTkButton(nav_bar, text="Home", width=80, command=lambda: show_page("home")).pack(side="left", padx=10, pady=10)
ctk.CTkButton(nav_bar, text="Add Categories", width=100, command=lambda: show_page("cat")).pack(side="left", padx=10)
ctk.CTkButton(nav_bar, text="Add Items", width=80, command=lambda: show_page("item")).pack(side="left", padx=10)
ctk.CTkButton(nav_bar, text="View Orders", width=100, command=lambda: show_page("orders")).pack(side="left", padx=10)

search_entry = ctk.CTkEntry(nav_bar, placeholder_text="Search food...")
search_entry.pack(side="right", fill="x", expand=True, padx=10)
search_entry.bind("<KeyRelease>", lambda e: update_grid())

# --- PAGE CONTENT AREA ---
content_area = ctk.CTkFrame(middle_panel_container, fg_color="transparent")
content_area.grid(row=1, column=0, sticky="nsew")
content_area.grid_columnconfigure(0, weight=1)
content_area.grid_rowconfigure(0, weight=1)

# 1. HOME PAGE
home_page = ctk.CTkFrame(content_area, fg_color="transparent")
foods_frame = ctk.CTkScrollableFrame(home_page)
foods_frame.pack(fill="both", expand=True, pady=0)
foods_frame.grid_columnconfigure((0, 1, 2), weight=1)

# 2. ADD CATEGORIES PAGE
add_cat_page = ctk.CTkFrame(content_area, fg_color="transparent")
cat_form = ctk.CTkFrame(add_cat_page, fg_color="#DBDBDB", corner_radius=15)
cat_form.pack(pady=20, padx=20, fill="x")

ctk.CTkLabel(cat_form, text="Category Name:", font=("Arial", 14, "bold"), text_color="black").pack(side="left", padx=15, pady=20)
cat_entry = ctk.CTkEntry(cat_form, placeholder_text="Enter category...", width=250)
cat_entry.pack(side="left", padx=10)

def handle_save_cat():
    name = cat_entry.get().strip()
    if name and save_category(name):
        cat_entry.delete(0, 'end')
        refresh_cat_table()
        refresh_sidebar()
        messagebox.showinfo("Success", "Category added!")

def handle_update_cat():
    global selected_cat_id
    name = cat_entry.get().strip()
    if selected_cat_id and name:
        if update_category_in_db(selected_cat_id, name):
            messagebox.showinfo("Success", "Category updated!")
            cat_entry.delete(0, 'end')
            selected_cat_id = None
            refresh_cat_table()
            refresh_sidebar()
    else:
        messagebox.showwarning("Selection", "Please select a category first.")

def handle_delete_cat():
    global selected_cat_id
    if selected_cat_id:
        msg = "Are you sure? This will fail if products are still linked to this category unless you have set up CASCADE delete in your DB."
        if messagebox.askyesno("Confirm Delete", msg):
            if delete_category_from_db(selected_cat_id):
                messagebox.showinfo("Success", "Category deleted!")
                cat_entry.delete(0, 'end')
                selected_cat_id = None
                refresh_cat_table()
                refresh_sidebar()
                refresh_products_grid()
    else:
        messagebox.showwarning("Selection", "Please select a category first.")

def on_cat_select(event):
    global selected_cat_id
    selected_item = cat_tree.focus()
    if selected_item:
        values = cat_tree.item(selected_item, 'values')
        selected_cat_id = values[0]
        cat_entry.delete(0, 'end')
        cat_entry.insert(0, values[1])

ctk.CTkButton(cat_form, text="Save", width=80, command=handle_save_cat).pack(side="left", padx=5)
ctk.CTkButton(cat_form, text="Update", width=80, fg_color="#fbbf24", hover_color="#d97706", text_color="black", command=handle_update_cat).pack(side="left", padx=5)
ctk.CTkButton(cat_form, text="Delete", width=80, fg_color="#ef4444", hover_color="#b91c1c", command=handle_delete_cat).pack(side="left", padx=5)

cat_table_frame = ctk.CTkFrame(add_cat_page, fg_color="white", corner_radius=15, height=350)
cat_table_frame.pack(pady=10, padx=20, fill="x")
cat_table_frame.pack_propagate(False)

cat_tree = ttk.Treeview(cat_table_frame, columns=("ID", "Name"), show="headings")
cat_tree.heading("ID", text="ID")
cat_tree.heading("Name", text="Category Name")
cat_tree.column("ID", width=100, anchor="center")
cat_tree.pack(fill="both", expand=True, padx=15, pady=15)
cat_tree.bind("<<TreeviewSelect>>", on_cat_select)

def refresh_cat_table():
    for item in cat_tree.get_children(): cat_tree.delete(item)
    for cid, name in fetch_categories_full(): cat_tree.insert("", "end", values=(cid, name))

# 3. ADD ITEMS PAGE
add_item_page = ctk.CTkFrame(content_area, fg_color="transparent")
item_form = ctk.CTkFrame(add_item_page, fg_color="#DBDBDB", corner_radius=15)
item_form.pack(pady=20, padx=20, fill="x")
item_form.columnconfigure((1, 3), weight=1)

ctk.CTkLabel(item_form, text="Food Name:", text_color="black").grid(row=0, column=0, padx=10, pady=10)
item_name_entry = ctk.CTkEntry(item_form)
item_name_entry.grid(row=0, column=1, sticky="ew", padx=10)
ctk.CTkLabel(item_form, text="Category:", text_color="black").grid(row=0, column=2, padx=10)
item_cat_dropdown = ctk.CTkOptionMenu(item_form, values=["Select Category"])
item_cat_dropdown.grid(row=0, column=3, sticky="ew", padx=10)
ctk.CTkLabel(item_form, text="Price (Rs):", text_color="black").grid(row=1, column=0, padx=10, pady=10)
item_price_entry = ctk.CTkEntry(item_form)
item_price_entry.grid(row=1, column=1, sticky="ew", padx=10)

def choose_image():
    global selected_image_path
    path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg")])
    if path:
        selected_image_path = path
        img_btn.configure(text=os.path.basename(path), fg_color="#28a745")

img_btn = ctk.CTkButton(item_form, text="Choose Image", command=choose_image, fg_color="#555")
img_btn.grid(row=1, column=2, columnspan=2, sticky="ew", padx=10)

def handle_save_item():
    name = item_name_entry.get().strip()
    cat = item_cat_dropdown.get()
    price = item_price_entry.get().strip()
    if not (name and price and selected_image_path and cat != "Select Category"):
        messagebox.showwarning("Error", "All fields are required!")
        return
    filename = os.path.basename(selected_image_path)
    if not os.path.exists("assets"): os.makedirs("assets")
    shutil.copy(selected_image_path, os.path.join("assets", filename))
    if save_product(name, cat, int(float(price)), filename):
        messagebox.showinfo("Success", "Product added!")
        clear_item_form()
        refresh_item_table()
        refresh_products_grid()

def handle_update_item():
    global selected_product_id, selected_image_path
    name = item_name_entry.get().strip()
    cat = item_cat_dropdown.get()
    price = item_price_entry.get().strip()
    if not selected_product_id:
        messagebox.showwarning("Selection", "Please select a product from the table.")
        return
    filename = None
    if selected_image_path:
        filename = os.path.basename(selected_image_path)
        if not os.path.exists("assets"): os.makedirs("assets")
        shutil.copy(selected_image_path, os.path.join("assets", filename))
    if update_product_in_db(selected_product_id, name, cat, int(float(price)), filename):
        messagebox.showinfo("Success", "Product updated!")
        clear_item_form()
        refresh_item_table()
        refresh_products_grid()

def handle_delete_item():
    global selected_product_id
    if selected_product_id:
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this product?"):
            if delete_product_from_db(selected_product_id):
                messagebox.showinfo("Success", "Product deleted!")
                clear_item_form()
                refresh_item_table()
                refresh_products_grid()
    else:
        messagebox.showwarning("Selection", "Please select a product first.")

def on_item_select(event):
    global selected_product_id, selected_image_path
    selected_item = item_tree.focus()
    if selected_item:
        values = item_tree.item(selected_item, 'values')
        selected_product_id = values[0]
        item_name_entry.delete(0, 'end')
        item_name_entry.insert(0, values[1])
        item_cat_dropdown.set(values[2])
        item_price_entry.delete(0, 'end')
        item_price_entry.insert(0, int(float(values[3])))
        img_btn.configure(text=values[4], fg_color="#28a745")
        selected_image_path = None

def clear_item_form():
    global selected_product_id, selected_image_path
    selected_product_id = None
    selected_image_path = None
    item_name_entry.delete(0, 'end')
    item_price_entry.delete(0, 'end')
    item_cat_dropdown.set("Select Category")
    img_btn.configure(text="Choose Image", fg_color="#555")

btn_frame = ctk.CTkFrame(item_form, fg_color="transparent")
btn_frame.grid(row=2, column=0, columnspan=4, pady=15)
ctk.CTkButton(btn_frame, text="Save Product", command=handle_save_item, width=120, height=40).pack(side="left", padx=10)
ctk.CTkButton(btn_frame, text="Update Product", command=handle_update_item, width=120, height=40, fg_color="#fbbf24", hover_color="#d97706", text_color="black").pack(side="left", padx=10)
ctk.CTkButton(btn_frame, text="Delete Product", command=handle_delete_item, width=120, height=40, fg_color="#ef4444", hover_color="#b91c1c").pack(side="left", padx=10)

item_table_frame = ctk.CTkFrame(add_item_page, fg_color="white", corner_radius=15, height=280)
item_table_frame.pack(pady=10, padx=20, fill="x")
item_table_frame.pack_propagate(False)

item_tree = ttk.Treeview(item_table_frame, columns=("ID", "Name", "Category", "Price", "Image"), show="headings")
for col in ("ID", "Name", "Category", "Price", "Image"):
    item_tree.heading(col, text=col)
    item_tree.column(col, width=100, anchor="center")
item_tree.pack(fill="both", expand=True, padx=15, pady=15)
item_tree.bind("<<TreeviewSelect>>", on_item_select)

def refresh_item_table():
    for item in item_tree.get_children(): item_tree.delete(item)
    for row in fetch_menu_full():
        cleaned_row = list(row)
        cleaned_row[3] = int(float(row[3]))
        item_tree.insert("", "end", values=cleaned_row)

def update_item_cat_dropdown():
    cats = fetch_categories()
    item_cat_dropdown.configure(values=cats)

# 4. VIEW ORDERS PAGE
view_orders_page = ctk.CTkFrame(content_area, fg_color="transparent")

order_search_frame = ctk.CTkFrame(view_orders_page, fg_color="#DBDBDB", corner_radius=15)
order_search_frame.pack(pady=20, padx=20, fill="x")
ctk.CTkLabel(order_search_frame, text="Search Order ID:", font=("Arial", 14, "bold"), text_color="black").pack(side="left", padx=15, pady=20)
order_search_entry = ctk.CTkEntry(order_search_frame, placeholder_text="Enter ID...", width=200)
order_search_entry.pack(side="left", padx=10)
order_search_entry.bind("<KeyRelease>", lambda e: refresh_orders_table())

def on_order_select(event):
    global selected_view_order_id
    selected_item = order_tree.focus()
    if selected_item:
        values = order_tree.item(selected_item, 'values')
        selected_view_order_id = values[0]

def handle_delete_order():
    global selected_view_order_id
    if selected_view_order_id:
        if messagebox.askyesno("Confirm", f"Delete Order #{selected_view_order_id}?"):
            if delete_order_from_db(selected_view_order_id):
                messagebox.showinfo("Success", "Order deleted!")
                selected_view_order_id = None
                refresh_orders_table()
    else:
        messagebox.showwarning("Selection", "Please select an order from the table.")

ctk.CTkButton(order_search_frame, text="Delete Order", fg_color="#ef4444", hover_color="#b91c1c", command=handle_delete_order).pack(side="right", padx=15)

order_table_frame = ctk.CTkFrame(view_orders_page, fg_color="white", corner_radius=15, height=400)
order_table_frame.pack(pady=10, padx=20, fill="x")
order_table_frame.pack_propagate(False)

order_tree = ttk.Treeview(order_table_frame, columns=("ID", "Date", "Total", "Items"), show="headings")
for col in ("ID", "Date", "Total", "Items"):
    order_tree.heading(col, text=col)
    order_tree.column(col, width=150, anchor="center")
order_tree.column("Items", width=400, anchor="w")
order_tree.pack(fill="both", expand=True, padx=15, pady=15)
order_tree.bind("<<TreeviewSelect>>", on_order_select)

def refresh_orders_table():
    for item in order_tree.get_children(): order_tree.delete(item)
    search_term = order_search_entry.get().strip()
    orders = fetch_orders()
    for row in orders:
        if not search_term or str(row[0]).startswith(search_term):
            cleaned_order = list(row)
            cleaned_order[2] = int(float(row[2]))
            order_tree.insert("", "end", values=cleaned_order)

# ================= HELPER FUNCTIONS ================= #
def get_clipped_image(img_path, target_size, radius):
    try:
        img = Image.open(img_path).convert("RGBA")
        img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
        mask = Image.new("L", target_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, target_size[0], target_size[1] + radius], radius=radius, fill=255)
        result = Image.new("RGBA", target_size, (0, 0, 0, 0))
        result.paste(img, (0, 0), mask=mask)
        return result
    except Exception:
        return None

def food_card(parent, name, price, img_path, category):
    card_width, img_height, corner_rad = 220, 140, 15
    card = ctk.CTkFrame(parent, height=270, corner_radius=corner_rad, fg_color="#DBDBDB")
    card.pack_propagate(False)
    card.category, card.food_name = category, name
    img = get_clipped_image(f"assets/{img_path}", (350, img_height), corner_rad)
    if img:
        ctk_img = ctk.CTkImage(light_image=img, size=(300, img_height))
        ctk_img_lbl = ctk.CTkLabel(card, text="", image=ctk_img)
        ctk_img_lbl.pack(side="top", fill="x")
    else:
        ctk.CTkLabel(card, text="No Image", height=img_height, fg_color="#e2e2e2").pack(fill="x")
    ctk.CTkLabel(card, text=name, font=("Arial", 16, "bold"), text_color="black").pack(pady=(10, 0))
    ctk.CTkLabel(card, text=f"Rs. {int(price)}", font=("Arial", 14), text_color="black").pack()
    btn_cont = ctk.CTkFrame(card, fg_color="transparent")
    btn_cont.pack(side="bottom", fill="x", padx=10, pady=10)
    ctk.CTkButton(btn_cont, text="Add", height=35, command=lambda: add_to_cart(name, price)).pack(fill="x", expand=True)
    return card

def refresh_products_grid():
    global food_cards
    for card in food_cards: card.destroy()
    food_cards.clear()
    foods_data = fetch_menu_from_db()
    for name, price, img, cat in foods_data:
        card = food_card(foods_frame, name, price, img, cat)
        food_cards.append(card)
    update_grid()

def update_grid(event=None):
    search_term = search_entry.get().lower()
    visible_cards = []
    for card in food_cards:
        if (current_category == "All" or card.category == current_category) and (search_term in card.food_name.lower()):
            visible_cards.append(card)
            card.grid()
        else:
            card.grid_forget()
    num_cols = 3
    for i, card in enumerate(visible_cards):
        card.grid(row=i // num_cols, column=i % num_cols, padx=15, pady=15, sticky="nsew")

# ================= CART & ORDER LOGIC ================= #
def add_to_cart(name, price):
    if name in cart_items:
        cart_items[name]["row"].increase()
    else:
        cart_items[name] = {"row": OrderItem(order_frame, name, price)}
    update_total()

def update_total():
    total = sum(item["row"].qty * item["row"].price for item in cart_items.values())
    total_label.configure(text=f"Total: Rs. {int(total)}")

def clear_cart():
    global cart_items
    for widget in order_frame.winfo_children():
        widget.destroy()
    cart_items.clear()
    update_total()

def handle_enter_button():
    if not cart_items:
        messagebox.showwarning("Empty Order", "Please add items to the cart first.")
        return
    total_val = sum(i["row"].qty * i["row"].price for i in cart_items.values())
    if save_order(cart_items, int(total_val)):
        messagebox.showinfo("Success", "Order placed successfully!")
        clear_cart()

class OrderItem(ctk.CTkFrame):
    def __init__(self, parent, name, price):
        super().__init__(parent, corner_radius=15)
        self.pack(fill="x", padx=10, pady=6)
        self.name, self.price, self.qty = name, price, 1
        self.expanded = False
        self.normal_color = self.cget("fg_color")
        self.selected_color = "#dbeafe"
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="x", padx=20, pady=15)
        self.container.bind("<Button-1>", self.toggle)
        self.name_lbl = ctk.CTkLabel(self.container, text=name, font=("Arial", 16, "bold"))
        self.name_lbl.pack(anchor="w", pady=(0, 5))
        self.name_lbl.bind("<Button-1>", self.toggle)
        self.info_row = ctk.CTkFrame(self.container, fg_color="transparent")
        self.info_row.pack(fill="x")
        self.info_row.bind("<Button-1>", self.toggle)
        self.price_lbl = ctk.CTkLabel(self.info_row, text=f"{int(price)}", font=("Arial", 14))
        self.price_lbl.pack(side="left")
        self.qty_lbl = ctk.CTkLabel(self.info_row, text="1", font=("Arial", 14))
        self.qty_lbl.pack(side="left", expand=True)
        self.total_lbl = ctk.CTkLabel(self.info_row, text=f"{int(price)}", font=("Arial", 14))
        self.total_lbl.pack(side="right")
        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkButton(self.controls, text="−", width=50, height=35, fg_color="#3b82f6", command=self.decrease).pack(side="left", padx=5)
        ctk.CTkButton(self.controls, text="+", width=50, height=35, fg_color="#3b82f6", command=self.increase).pack(side="left", padx=5)
        ctk.CTkButton(self.controls, text="🗑", width=50, height=35, fg_color="#ef4444", command=self.delete).pack(side="left", padx=5)

    def toggle(self, event=None):
        if self.expanded:
            self.controls.pack_forget()
            self.configure(fg_color=self.normal_color)
        else:
            self.controls.pack(pady=(0, 10))
            self.configure(fg_color=self.selected_color)
        self.expanded = not self.expanded

    def increase(self):
        self.qty += 1
        self.update_view()
        update_total()

    def decrease(self):
        if self.qty > 1:
            self.qty -= 1
            self.update_view()
            update_total()

    def delete(self):
        if self.name in cart_items: del cart_items[self.name]
        self.destroy()
        update_total()

    def update_view(self):
        self.qty_lbl.configure(text=f"{self.qty}")
        self.total_lbl.configure(text=f"{int(self.qty * self.price)}")

# ================= RIGHT PANEL ================= #
right_frame = ctk.CTkFrame(app, width=350)
right_frame.grid(row=0, column=2, sticky="nse", padx=5, pady=5)
right_frame.grid_propagate(False)

ctk.CTkLabel(right_frame, text="Order List", font=("Arial", 22, "bold")).pack(pady=15)
order_frame = ctk.CTkScrollableFrame(right_frame, height=380)
order_frame.pack(fill="both", expand=True, padx=10, pady=5)

bottom_panel = ctk.CTkFrame(right_frame, fg_color="#e0e0e0", corner_radius=10)
bottom_panel.pack(fill="x", padx=15, pady=15)

total_label = ctk.CTkLabel(bottom_panel, text="Total: Rs. 0", font=("Arial", 18, "bold"))
total_label.pack(pady=10)

enter_btn = ctk.CTkButton(bottom_panel, text="Enter", width=250, height=45,
                          fg_color="#28a745", hover_color="#218838", font=("Arial", 16, "bold"),
                          command=handle_enter_button)
enter_btn.pack(pady=(0, 15))

# ================= INITIALIZATION ================= #
refresh_sidebar()
refresh_products_grid()
show_page("home")

app.mainloop()