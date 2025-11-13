import streamlit as st
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
import os

# ---------------------------
# Configuration & DB helper
# ---------------------------

@st.cache_resource
def get_db():
    # Expect secrets in Streamlit secrets or environment variables
    # [mongodb]
    # uri = "YOUR_MONGODB_URI"
    # [admin]
    # username = "admin"
    # password = "your_admin_password"

    mongodb_uri = None
    admin_user = None
    admin_password = None

    if "mongodb" in st.secrets:
        mongodb_uri = st.secrets["mongodb"].get("uri")
    else:
        mongodb_uri = os.environ.get("MONGODB_URI")

    if "admin" in st.secrets:
        admin_user = st.secrets["admin"].get("username")
        admin_password = st.secrets["admin"].get("password")
    else:
        admin_user = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")

    if not mongodb_uri:
        st.error("MongoDB URI not found. Please set it in Streamlit secrets or environment variables.")
        st.stop()

    client = MongoClient(mongodb_uri)
    db = client.get_default_database()
    if db is None:
        db = client["streamlit_store"]

    users = db.users
    products = db.products
    orders = db.orders

    # Ensure admin user exists
    if admin_user and admin_password:
        if users.find_one({"username": admin_user, "role": "admin"}) is None:
            hashed = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt())
            users.insert_one({"username": admin_user, "password": hashed, "role": "admin"})

    return {
        "client": client,
        "db": db,
        "users": users,
        "products": products,
        "orders": orders,
    }

# ---------------------------
# Database Collections
# ---------------------------

dbs = get_db()
users_col = dbs["users"]
products_col = dbs["products"]
orders_col = dbs["orders"]

# ---------------------------
# Utility functions
# ---------------------------

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed)
    except Exception:
        return False

def create_user(username: str, password: str, role: str = "user"):
    if users_col.find_one({"username": username}):
        return False, "User already exists"
    hashed = hash_password(password)
    users_col.insert_one({"username": username, "password": hashed, "role": role})
    return True, "User created successfully"

def create_product(name: str, price: float):
    products_col.insert_one({"name": name, "price": float(price)})
    return True

def list_products():
    return list(products_col.find())

def authenticate(username: str, password: str):
    user = users_col.find_one({"username": username})
    if not user:
        return None
    if check_password(password, user["password"]):
        return {
            "_id": user.get("_id"),
            "username": user.get("username"),
            "role": user.get("role", "user"),
        }
    return None

def place_order(user_id, username, cart_items):
    total = sum(item["price"] * item.get("qty", 1) for item in cart_items)

    # Convert to ObjectId safely
    try:
        user_oid = ObjectId(str(user_id))
    except Exception:
        user_oid = user_id

    order = {
        "user_id": user_oid,
        "username": username,
        "items": cart_items,
        "total": total,
        "status": "placed",
    }
    orders_col.insert_one(order)
    return order

# ---------------------------
# Streamlit App UI
# ---------------------------

st.set_page_config(page_title="Mini Store", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "login"

if "user" not in st.session_state:
    st.session_state.user = None

if "cart" not in st.session_state:
    st.session_state.cart = []

def logout():
    st.session_state.user = None
    st.session_state.cart = []
    st.session_state.page = "login"

# ---------------------------
# Top Bar
# ---------------------------

col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    st.title("🛍️ Mini Store")
with col3:
    if st.session_state.user:
        st.write(f"**{st.session_state.user['username']}** ({st.session_state.user['role']})")
        if st.button("Logout"):
            logout()

# ---------------------------
# Page Routing
# ---------------------------

if st.session_state.page == "login":
    st.header("Login")

    tab1, tab2 = st.tabs(["Admin Login", "User Login"])

    with tab1:
        st.subheader("Admin Login")
        admin_username = st.text_input("Admin username", key="admin_username")
        admin_password = st.text_input("Admin password", type="password", key="admin_password")
        if st.button("Login as Admin"):
            user = authenticate(admin_username, admin_password)
            if user and user.get("role") == "admin":
                st.session_state.user = user
                st.session_state.page = "admin"
                st.success("✅ Admin login successful")
            else:
                st.error("Invalid admin credentials")

    with tab2:
        st.subheader("User Login")
        username = st.text_input("Username", key="user_username")
        password = st.text_input("Password", type="password", key="user_password")
        if st.button("Login as User"):
            user = authenticate(username, password)
            if user and user.get("role") == "user":
                st.session_state.user = user
                st.session_state.page = "store"
                st.success("✅ User login successful")
            else:
                st.error("Invalid username or password")

elif st.session_state.page == "admin":
    st.header("👑 Admin Dashboard")

    st.subheader("Create a New User")
    with st.form("create_user_form"):
        new_username = st.text_input("New user's username")
        new_password = st.text_input("New user's password", type="password")
        submitted = st.form_submit_button("Create user")
        if submitted:
            ok, msg = create_user(new_username, new_password)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.subheader("Add a New Product")
    with st.form("create_product_form"):
        pname = st.text_input("Product name")
        pprice = st.number_input("Price (₹)", min_value=0.0, format="%.2f")
        submitted_p = st.form_submit_button("Add Product")
        if submitted_p:
            if pname:
                create_product(pname, pprice)
                st.success("✅ Product added successfully")
            else:
                st.error("Please enter a product name")

    st.subheader("Current Products")
    prods = list_products()
    if prods:
        for p in prods:
            st.write(f"- **{p.get('name')}** — ₹{p.get('price')}")
    else:
        st.info("No products added yet.")

    if st.button("⬅ Back to Login"):
        logout()

elif st.session_state.page == "store":
    st.header("🛒 Available Products")

    prods = list_products()
    if not prods:
        st.info("No products available. Please wait for admin to add some.")
    else:
        cols = st.columns(3)
        for i, p in enumerate(prods):
            col = cols[i % 3]
            with col:
                st.subheader(p.get("name"))
                st.write(f"💰 Price: ₹{p.get('price')}")
                qty = st.number_input(f"Quantity for {p.get('name')}", min_value=1, value=1, key=f"qty_{i}")
                if st.button(f"Add {p.get('name')} to Cart", key=f"add_{i}"):
                    st.session_state.cart.append({
                        "product_id": str(p.get("_id")),
                        "name": p.get("name"),
                        "price": float(p.get("price")),
                        "qty": int(qty),
                    })
                    st.success(f"Added {p.get('name')} (x{qty}) to cart")

    # Sidebar Cart
    st.sidebar.header("🧺 Your Cart")
    if st.session_state.cart:
        total = 0
        for item in st.session_state.cart:
            line_total = item["price"] * item.get("qty", 1)
            total += line_total
            st.sidebar.write(f"{item['name']} x{item['qty']} — ₹{line_total:.2f}")
        st.sidebar.markdown(f"**Total: ₹{total:.2f}**")

        if st.sidebar.button("✅ Place Order"):
            user = st.session_state.user
            if user:
                place_order(user["_id"], user["username"], st.session_state.cart)
                st.session_state.cart = []
                st.success("🎉 Order placed successfully!")
                st.balloons()
            else:
                st.error("Please log in again to place order.")
    else:
        st.sidebar.info("Your cart is empty")

    if st.button("⬅ Back to Login"):
        logout()

# EOF
