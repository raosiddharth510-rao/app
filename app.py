import streamlit as st
with st.form("create_user_form"):
new_username = st.text_input("New user's username")
new_password = st.text_input("New user's password", type="password")
submitted = st.form_submit_button("Create user")
if submitted:
ok, msg = create_user(new_username, new_password, role="user")
if ok:
st.success(msg)
else:
st.error(msg)


st.subheader("Create product")
with st.form("create_product_form"):
pname = st.text_input("Product name")
pprice = st.number_input("Price", min_value=0.0, format="%.2f")
submitted_p = st.form_submit_button("Create product")
if submitted_p:
if pname and pprice >= 0:
create_product(pname, pprice)
st.success("Product created")
else:
st.error("Enter valid product name and price")


st.subheader("Products list")
prods = list_products()
if prods:
for p in prods:
st.write(f"- {p.get('name')} — ₹{p.get('price')}")
else:
st.write("No products yet.")


if st.button("Back to login"):
logout()




elif st.session_state.page == "store":
st.header("Products")
prods = list_products()


cols = st.columns(3)
for i, p in enumerate(prods):
col = cols[i % 3]
with col:
st.subheader(p.get("name"))
st.write(f"Price: ₹{p.get('price')}")
qty = st.number_input(f"Quantity_{i}", min_value=1, value=1, key=f"qty_{i}")
if st.button("Add to cart", key=f"add_{i}"):
st.session_state.cart.append({
"product_id": str(p.get("_id")),
"name": p.get("name"),
"price": float(p.get("price")),
"qty": int(qty),
})
st.success("Added to cart")


st.sidebar.header("Cart")
if st.session_state.cart:
for idx, item in enumerate(st.session_state.cart):
st.sidebar.write(f"{item['name']} x{item.get('qty',1)} — ₹{item['price']*item.get('qty',1)}")
if st.sidebar.button("Buy now"):
if st.session_state.user:
order = place_order(st.session_state.user["_id"], st.session_state.user["username"], st.session_state.cart)
st.session_state.cart = []
st.success("Order placed successfully.")
st.balloons()
else:
st.error("You must be logged in to buy")
else:
st.sidebar.write("Cart is empty")


if st.button("Back to login"):
logout()




# EOF