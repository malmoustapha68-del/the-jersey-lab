import json
import os
import hmac
from pathlib import Path
from urllib.parse import quote
from datetime import datetime
import streamlit as st

st.set_page_config(page_title='THE JERSEY LAB — BY MOMO', page_icon='⚽', layout='wide')
DATA = Path('data'); UPLOADS = Path('uploads')
DATA.mkdir(exist_ok=True); UPLOADS.mkdir(exist_ok=True)
PRODUCTS = DATA / 'products.json'; ORDERS = DATA / 'orders.json'
WHATSAPP = '2250141766774'

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    except (OSError, ValueError):
        return default

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def fcfa(value):
    return f'{int(value):,}'.replace(',', ' ') + ' FCFA'

if not PRODUCTS.exists(): write_json(PRODUCTS, [])
if not ORDERS.exists(): write_json(ORDERS, [])
if 'cart' not in st.session_state: st.session_state.cart = []
if 'admin' not in st.session_state: st.session_state.admin = False
if 'page' not in st.session_state: st.session_state.page = 'Boutique'

st.markdown('''<style>
.stApp {background:#f8f7f5;color:#151515}
.block-container {max-width:1250px;padding-top:1.5rem}
h1,h2,h3 {font-family:Georgia,serif;letter-spacing:-.025em}
.brand {font-family:Georgia,serif;font-size:clamp(2.2rem,6vw,4.5rem);font-weight:bold;line-height:1.1}
.brand span {color:#c97f9e}.eyebrow {letter-spacing:.25em;font-size:.72rem;color:#777}
.subtitle {color:#666;max-width:640px;line-height:1.7}
.product {background:white;border:1px solid #eae5e3;padding:15px;border-radius:5px;margin-bottom:8px}
.category {font-size:.7rem;color:#999;letter-spacing:.15em;text-transform:uppercase}
.price {font-size:1.2rem;font-weight:700}.muted {color:#777;font-size:.9rem}
.stButton button[kind=primary] {background:#151515;color:white;border-color:#151515;border-radius:3px}
.stButton button[kind=primary]:hover {background:#c97f9e;border-color:#c97f9e;color:white}
</style>''', unsafe_allow_html=True)

products = read_json(PRODUCTS, [])
st.markdown('<div class="eyebrow">SÉLECTION FOOTBALL · CÔTE D’IVOIRE</div>', unsafe_allow_html=True)
st.markdown('<div class="brand">THE JERSEY <span>LAB</span></div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">BY MOMO — Des maillots choisis pour les passionnés. Une sélection simple, un style affirmé, une commande directe.</p>', unsafe_allow_html=True)
st.caption(f'🛍️ Panier : {sum(x["quantity"] for x in st.session_state.cart)} article(s)')
nav = st.radio('Navigation', ['Boutique', 'Mon panier', 'Administration'], horizontal=True, index=['Boutique','Mon panier','Administration'].index(st.session_state.page))
st.session_state.page = nav
st.divider()

if nav == 'Boutique':
    st.header('La sélection')
    st.caption('Choisis ton maillot et ajoute-le au panier sans quitter la boutique.')
    available = [p for p in products if p.get('available', True)]
    categories = ['Toutes'] + sorted({p.get('category','Autre') for p in available})
    a,b = st.columns([1,2]); category = a.selectbox('Catégorie', categories); search = b.text_input('Rechercher', placeholder='Club, sélection, maillot…')
    visible = [p for p in available if (category == 'Toutes' or p.get('category') == category) and search.casefold() in p.get('name','').casefold()]
    if not visible: st.info('Aucun maillot disponible pour cette recherche. Connecte-toi à l’administration pour en ajouter.')
    for start in range(0,len(visible),3):
        cols = st.columns(3, gap='large')
        for col,p in zip(cols,visible[start:start+3]):
            with col:
                st.markdown('<div class="product">', unsafe_allow_html=True)
                image = p.get('image','')
                if image and (image.startswith(('https://','http://')) or Path(image).is_file()):
                    st.image(image, use_container_width=True)
                else: st.markdown('<div style="height:180px;background:#eeecea;display:flex;align-items:center;justify-content:center;font-size:50px">⚽</div>', unsafe_allow_html=True)
                st.markdown(f'<p class="category">{p.get("category","Maillot")}</p>', unsafe_allow_html=True)
                st.subheader(p.get('name','Maillot'))
                st.markdown(f'<p class="price">{fcfa(p.get("price",0))}</p>', unsafe_allow_html=True)
                if p.get('description'): st.caption(p['description'])
                sizes = p.get('sizes',['S','M','L','XL'])
                if isinstance(sizes,str): sizes = [x.strip() for x in sizes.split(',') if x.strip()]
                size = st.selectbox('Taille',sizes or ['M'],key=f'size_{p["id"]}')
                qty = st.number_input('Quantité',1,20,1,key=f'qty_{p["id"]}')
                if st.button('Ajouter au panier',key=f'add_{p["id"]}',type='primary',use_container_width=True):
                    existing = next((x for x in st.session_state.cart if x['id']==p['id'] and x['size']==size),None)
                    if existing: existing['quantity'] += qty
                    else: st.session_state.cart.append({'id':p['id'],'name':p['name'],'price':int(p['price']),'size':size,'quantity':qty})
                    st.toast('Maillot ajouté au panier !',icon='🛍️'); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)

elif nav == 'Mon panier':
    st.header('Mon panier')
    cart = st.session_state.cart
    if not cart: st.info('Ton panier est vide. Va dans Boutique pour choisir tes maillots.')
    else:
        total = 0
        for i,item in enumerate(cart):
            c1,c2,c3,c4 = st.columns([4,1,2,1]); c1.write(f'**{item["name"]}** — Taille {item["size"]}')
            new_qty = c2.number_input('Qté',1,20,int(item['quantity']),key=f'cartqty_{i}')
            item['quantity'] = new_qty
            line = item['price']*new_qty; total += line; c3.write(fcfa(line))
            if c4.button('Retirer',key=f'del_{i}'):
                cart.pop(i); st.rerun()
            st.divider()
        st.subheader(f'Total : {fcfa(total)}')
        with st.form('order'):
            name = st.text_input('Nom complet *'); phone = st.text_input('Téléphone *'); city = st.text_input('Ville / commune *'); note = st.text_area('Précisions de livraison (facultatif)')
            submitted = st.form_submit_button('Préparer ma commande WhatsApp',type='primary')
        if submitted:
            if not all(x.strip() for x in [name,phone,city]): st.error('Renseigne ton nom, ton téléphone et ta ville.')
            else:
                lines = ['Bonjour THE JERSEY LAB — BY MOMO, je souhaite commander :','']
                for x in cart: lines.append(f'• {x["name"]} | Taille {x["size"]} | Quantité {x["quantity"]} | {fcfa(x["price"]*x["quantity"])}')
                lines += ['',f'TOTAL : {fcfa(total)}',f'Nom : {name}',f'Téléphone : {phone}',f'Ville / commune : {city}']
                if note.strip(): lines.append(f'Précision : {note.strip()}')
                url = f'https://wa.me/{WHATSAPP}?text={quote(chr(10).join(lines))}'
                st.link_button('Ouvrir WhatsApp et envoyer',url,type='primary',use_container_width=True)
                st.caption('La commande est envoyée uniquement après validation du message dans WhatsApp.')

else:
    st.header('Administration')
    if not st.session_state.admin:
        with st.form('login'):
            password = st.text_input('Mot de passe',type='password')
            login = st.form_submit_button('Se connecter',type='primary')
        if login:
            try: configured = st.secrets.get('ADMIN_PASSWORD','')
            except Exception: configured = ''
            configured = configured or os.environ.get('ADMIN_PASSWORD','')
            if configured and hmac.compare_digest(password,str(configured)):
                st.session_state.admin = True; st.rerun()
            else: st.error('Mot de passe incorrect ou ADMIN_PASSWORD non configuré dans Streamlit Secrets.')
    else:
        if st.button('Se déconnecter'): st.session_state.admin = False; st.rerun()
        add,manage,orders_tab = st.tabs(['Ajouter un maillot','Gérer les maillots','Commandes'])
        with add:
            with st.form('add_product',clear_on_submit=True):
                name = st.text_input('Nom du maillot *'); category = st.selectbox('Catégorie',['Club','Sélection','Rétro','Autre'])
                price = st.number_input('Prix (FCFA)',min_value=0,value=15000,step=500)
                sizes = st.text_input('Tailles (séparées par des virgules)',value='S, M, L, XL')
                description = st.text_area('Description'); image_url = st.text_input('URL de photo (facultatif)')
                uploaded = st.file_uploader('Ou importer une photo',type=['jpg','jpeg','png','webp'])
                available = st.checkbox('Disponible',value=True)
                submitted = st.form_submit_button('Ajouter le produit',type='primary')
            if submitted:
                if not name.strip(): st.error('Le nom est obligatoire.')
                else:
                    image = image_url.strip()
                    if uploaded:
                        safe = ''.join(ch for ch in uploaded.name if ch.isalnum() or ch in '._-')
                        dest = UPLOADS / f'{int(datetime.now().timestamp())}_{safe}'
                        dest.write_bytes(uploaded.getvalue()); image = str(dest)
                    new_id = max([int(p.get('id',0)) for p in products]+[0])+1
                    products.append({'id':new_id,'name':name.strip(),'category':category,'price':int(price),'sizes':[s.strip().upper() for s in sizes.split(',') if s.strip()] or ['M'],'description':description.strip(),'image':image,'available':available})
                    write_json(PRODUCTS,products); st.success('Produit ajouté.'); st.rerun()
        with manage:
            if not products: st.info('Aucun produit.')
            for p in products:
                with st.expander(f'{p.get("name","Maillot")} — {fcfa(p.get("price",0))}'):
                    with st.form(f'edit_{p["id"]}'):
                        new_name = st.text_input('Nom',value=p.get('name',''))
                        new_price = st.number_input('Prix',min_value=0,value=int(p.get('price',0)),step=500)
                        new_cat = st.text_input('Catégorie',value=p.get('category','Club'))
                        old_sizes = p.get('sizes',[])
                        new_sizes = st.text_input('Tailles',value=', '.join(old_sizes) if isinstance(old_sizes,list) else old_sizes)
                        new_desc = st.text_area('Description',value=p.get('description',''))
                        new_image = st.text_input('Lien / chemin de photo',value=p.get('image',''))
                        new_available = st.checkbox('Disponible',value=p.get('available',True))
                        c1,c2 = st.columns(2); save = c1.form_submit_button('Enregistrer'); delete = c2.form_submit_button('Supprimer')
                    if save:
                        p.update(name=new_name.strip(),price=int(new_price),category=new_cat.strip(),sizes=[s.strip().upper() for s in new_sizes.split(',') if s.strip()] or ['M'],description=new_desc.strip(),image=new_image.strip(),available=new_available)
                        write_json(PRODUCTS,products); st.rerun()
                    if delete:
                        write_json(PRODUCTS,[x for x in products if x['id']!=p['id']]); st.rerun()
        with orders_tab:
            st.info('Les commandes WhatsApp ne sont pas automatiquement enregistrées ici. Le client doit envoyer son message dans WhatsApp.')
            saved_orders = read_json(ORDERS,[])
            if saved_orders: st.json(saved_orders)

st.divider()
st.caption('THE JERSEY LAB — BY MOMO · Prix des articles hors éventuels frais de livraison. Les données et images enregistrées localement peuvent disparaître après un redémarrage de Streamlit Cloud : prévoir un stockage persistant avant le lancement commercial.')