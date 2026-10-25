import streamlit as st
import os
import json
import hashlib
import hmac
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

st.set_page_config(
    page_title="THE JERSEY LAB — BY MOMO",
    page_icon="⚽",
    layout="wide"
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DATA_DIR = Path("data")
UPLOAD_DIR = Path("uploads")
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"

# Le mot de passe sera configuré dans Streamlit Secrets.
# Ne place jamais ton vrai mot de passe dans le code public.


def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        st.error(f"Impossible de lire le fichier {path.name}.")
    return default


def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def money(value):
    return f"{int(value):,}".replace(",", " ") + " FCFA"


def init_data():
    if not PRODUCTS_FILE.exists():
        save_json(PRODUCTS_FILE, [])
    if not ORDERS_FILE.exists():
        save_json(ORDERS_FILE, [])


init_data()


# --------------------------------------------------
# STYLE
# --------------------------------------------------

st.markdown("""
<style>
.stApp {
    background: #090909;
    color: #ffffff;
}
h1, h2, h3 {
    color: #ff3d9a !important;
}
.lab-banner {
    background: linear-gradient(135deg, #191919, #080808);
    border: 1px solid #ff3d9a;
    border-radius: 15px;
    padding: 28px 12px;
    text-align: center;
    margin-bottom: 24px;
}
.lab-title {
    color: #ff3d9a;
    font-size: clamp(30px, 7vw, 54px);
    font-weight: 900;
    letter-spacing: 2px;
}
.lab-subtitle {
    color: white;
    letter-spacing: 5px;
}
.product {
    background: #161616;
    border: 1px solid #333333;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 15px;
}
.price {
    color: #ff3d9a;
    font-size: 23px;
    font-weight: bold;
}
.stButton > button {
    border: 1px solid #ff3d9a;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# EN-TÊTE
# --------------------------------------------------

st.markdown("""
<div class="lab-banner">
    <div class="lab-title">THE JERSEY LAB</div>
    <div class="lab-subtitle">BY MOMO</div>
    <p>FOOTBALL CULTURE • STREETWEAR • IDENTITY</p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# SESSION
# --------------------------------------------------

if "cart" not in st.session_state:
    st.session_state.cart = {}

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False


# --------------------------------------------------
# DONNÉES
# --------------------------------------------------

products = load_json(PRODUCTS_FILE, [])
orders = load_json(ORDERS_FILE, [])


# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------

page = st.radio(
    "Navigation",
    ["Boutique", "Mon panier", "Administration"],
    horizontal=True
)


# --------------------------------------------------
# BOUTIQUE PUBLIQUE
# --------------------------------------------------

if page == "Boutique":
    st.header("⚡ LE LABORATOIRE DU MAILLOT")
    st.write("Le football rencontre le streetwear.")

    search = st.text_input(
        "Rechercher un maillot",
        placeholder="Nom du club ou du modèle..."
    )

    visible = [
        p for p in products
        if search.lower() in p["name"].lower()
        and int(p.get("stock", 0)) > 0
    ]

    if not visible:
        st.info(
            "Aucun maillot disponible pour le moment. "
            "Les nouveaux modèles seront affichés ici."
        )

    columns = st.columns(2)

    for index, product in enumerate(visible):
        with columns[index % 2]:
            st.markdown('<div class="product">', unsafe_allow_html=True)

            photo = product.get("photo", "")
            if photo and Path(photo).exists():
                st.image(photo, use_container_width=True)
            else:
                st.markdown("## ⚽")

            st.subheader(product["name"])
            st.caption(product.get("category", "Sélection du Lab"))

            st.markdown(
                f'<div class="price">{money(product["price"])}</div>',
                unsafe_allow_html=True
            )

            sizes = product.get("sizes", ["M", "L", "XL"])
            size = st.selectbox(
                "Taille",
                sizes,
                key=f"size_{product['id']}"
            )

            st.caption(f"En stock : {product['stock']}")

            if st.button(
                "＋ Ajouter au panier",
                key=f"add_{product['id']}"
            ):
                key = f"{product['id']}|{size}"
                st.session_state.cart[key] = (
                    st.session_state.cart.get(key, 0) + 1
                )
                st.success("Ajouté au panier !")

            st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------
# PANIER ET COMMANDE WHATSAPP
# --------------------------------------------------

elif page == "Mon panier":
    st.header("🛒 MON PANIER")

    products_by_id = {str(p["id"]): p for p in products}
    total = 0
    message_lines = ["Bonjour THE JERSEY LAB — BY MOMO !"]
    valid_items = []

    for key, quantity in list(st.session_state.cart.items()):
        product_id, size = key.split("|", 1)
        product = products_by_id.get(product_id)

        if not product:
            continue

        subtotal = int(product["price"]) * quantity
        total += subtotal
        valid_items.append((key, product, size, quantity))

        st.write(
            f"**{product['name']}** — Taille {size} — "
            f"{quantity} × {money(product['price'])}"
        )

        message_lines.append(
            f"- {product['name']} / Taille {size} / Quantité : {quantity}"
        )

        if st.button("Retirer", key=f"remove_{key}"):
            del st.session_state.cart[key]
            st.rerun()

    if valid_items:
        st.divider()
        st.subheader(f"Total indicatif : {money(total)}")

        client_name = st.text_input("Ton nom")
        client_phone = st.text_input("Ton numéro de téléphone")
        client_city = st.text_input("Ta commune")

        if client_name and client_phone and client_city:
            message_lines.extend([
                f"Nom : {client_name}",
                f"Téléphone : {client_phone}",
                f"Commune : {client_city}",
                f"Total indicatif : {money(total)}",
                "Merci de confirmer la disponibilité et les modalités."
            ])

            whatsapp_message = quote("\n".join(message_lines))
            whatsapp_link = (
                "https://wa.me/2250141766774?text="
                + whatsapp_message
            )

            st.link_button(
                "📲 Continuer sur WhatsApp",
                whatsapp_link
            )

            st.caption(
                "La commande n'est pas confirmée tant que "
                "la boutique n'a pas validé la disponibilité."
            )
        else:
            st.info("Renseigne ton nom, ton téléphone et ta commune.")
    else:
        st.info("Ton panier est vide.")


# --------------------------------------------------
# ADMINISTRATION
# --------------------------------------------------

elif page == "Administration":
    st.header("🔐 ESPACE ADMINISTRATEUR")

    try:
        admin_password = st.secrets["ADMIN_PASSWORD"]
    except Exception:
        admin_password = os.environ.get("ADMIN_PASSWORD", "")

    if not admin_password:
        st.warning(
            "L'accès administrateur n'est pas encore configuré. "
            "Nous le sécuriserons lors du déploiement."
        )
    elif not st.session_state.admin_logged_in:
        entered_password = st.text_input(
            "Mot de passe administrateur",
            type="password"
        )

        if st.button("Se connecter"):
            if hmac.compare_digest(entered_password, admin_password):
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")

    else:
        if st.button("Se déconnecter"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.success("Bienvenue dans ton espace de gestion.")

        # STATISTIQUES
        stock_count = sum(int(p.get("stock", 0)) for p in products)
        st.metric("Modèles de maillots", len(products))
        st.metric("Maillots en stock", stock_count)
        st.metric("Commandes enregistrées", len(orders))

        tab_add, tab_manage, tab_orders = st.tabs([
            "Ajouter un maillot",
            "Gérer les maillots",
            "Commandes WhatsApp"
        ])

        # AJOUTER UN PRODUIT
        with tab_add:
            st.subheader("Ajouter un nouveau modèle")

            with st.form("add_product_form", clear_on_submit=True):
                name = st.text_input("Nom du maillot")
                category = st.text_input("Catégorie / Club")

                price = st.number_input(
                    "Prix de vente (FCFA)",
                    min_value=0,
                    value=3500,
                    step=500
                )

                cost = st.number_input(
                    "Coût d'achat unitaire (FCFA)",
                    min_value=0,
                    value=1250,
                    step=250
                )

                stock = st.number_input(
                    "Quantité en stock",
                    min_value=0,
                    value=1,
                    step=1
                )

                sizes_text = st.text_input(
                    "Tailles disponibles, séparées par des virgules",
                    value="S, M, L, XL"
                )

                uploaded_photo = st.file_uploader(
                    "Photo du maillot",
                    type=["jpg", "jpeg", "png", "webp"]
                )

                submitted = st.form_submit_button("Enregistrer le maillot")

                if submitted:
                    if not name.strip():
                        st.error("Donne un nom au maillot.")
                    elif int(price) <= 0:
                        st.error("Le prix doit être supérieur à zéro.")
                    else:
                        photo_path = ""

                        if uploaded_photo:
                            safe_name = (
                                f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                                f"_{Path(uploaded_photo.name).name}"
                            )
                            photo_path = str(UPLOAD_DIR / safe_name)

                            with open(photo_path, "wb") as photo_file:
                                photo_file.write(uploaded_photo.getvalue())

                        new_product = {
                            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                            "name": name.strip(),
                            "category": category.strip(),
                            "price": int(price),
                            "cost": int(cost),
                            "stock": int(stock),
                            "sizes": [
                                s.strip()
                                for s in sizes_text.split(",")
                                if s.strip()
                            ],
                            "photo": photo_path
                        }

                        products.append(new_product)
                        save_json(PRODUCTS_FILE, products)
                        st.success(
                            "Maillot ajouté. Attention : le stockage "
                            "sera fiabilisé avant la mise en ligne."
                        )
                        st.rerun()

        # GÉRER LES PRODUITS
        with tab_manage:
            st.subheader("Modifier ou supprimer un maillot")

            if not products:
                st.info("Tu n'as pas encore ajouté de maillot.")
            else:
                for product in products:
                    with st.expander(product["name"]):
                        st.write(
                            f"Prix : {money(product['price'])} — "
                            f"Stock : {product['stock']}"
                        )

                        new_price = st.number_input(
                            "Nouveau prix",
                            min_value=0,
                            value=int(product["price"]),
                            step=500,
                            key=f"price_{product['id']}"
                        )

                        new_stock = st.number_input(
                            "Nouvelle quantité",
                            min_value=0,
                            value=int(product["stock"]),
                            step=1,
                            key=f"stock_{product['id']}"
                        )

                        col_save, col_delete = st.columns(2)

                        with col_save:
                            if st.button(
                                "Enregistrer",
                                key=f"save_{product['id']}"
                            ):
                                for item in products:
                                    if item["id"] == product["id"]:
                                        item["price"] = int(new_price)
                                        item["stock"] = int(new_stock)

                                save_json(PRODUCTS_FILE, products)
                                st.success("Modifications enregistrées.")
                                st.rerun()

                        with col_delete:
                            if st.button(
                                "Supprimer",
                                key=f"delete_{product['id']}"
                            ):
                                products = [
                                    item for item in products
                                    if item["id"] != product["id"]
                                ]
                                save_json(PRODUCTS_FILE, products)
                                st.rerun()

        # SUIVI MANUEL DES COMMANDES
        with tab_orders:
            st.subheader("Enregistrer une commande reçue sur WhatsApp")

            with st.form("add_order_form", clear_on_submit=True):
                order_client = st.text_input("Nom du client")
                order_phone = st.text_input("Téléphone du client")
                order_amount = st.number_input(
                    "Montant de la commande (FCFA)",
                    min_value=0,
                    step=500
                )
                order_status = st.selectbox(
                    "Statut",
                    ["À confirmer", "Confirmée", "Payée", "Livrée", "Annulée"]
                )

                order_submitted = st.form_submit_button(
                    "Enregistrer la commande"
                )

                if order_submitted:
                    if not order_client.strip():
                        st.error("Indique le nom du client.")
                    else:
                        orders.append({
                            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                            "client": order_client.strip(),
                            "phone": order_phone.strip(),
                            "amount": int(order_amount),
                            "status": order_status,
                            "date": datetime.now().isoformat(timespec="minutes")
                        })
                        save_json(ORDERS_FILE, orders)
                        st.success("Commande enregistrée.")
                        st.rerun()

            if orders:
                st.divider()
                for order in reversed(orders):
                    st.write(
                        f"**{order['client']}** — "
                        f"{money(order['amount'])} — "
                        f"{order['status']} — {order['date']}"
                    )


# --------------------------------------------------
# PIED DE PAGE
# --------------------------------------------------

st.divider()
st.markdown(
    "<center>THE JERSEY LAB — BY MOMO<br>"
    "FOOTBALL MEETS STREETWEAR 🖤🩷🤍</center>",
    unsafe_allow_html=True
)