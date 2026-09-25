from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "clave_secreta_super_segura_100"  # Necesario para manejar sesiones de admin

# PIN temporal de seguridad de las mesas
PIN_NOCHE = "7420"
# Clave exclusiva para el Panel de Administrador / Gerencia
PIN_ADMIN = "100admin"

# Estructura centralizada de las 40 mesas
mesas_estado = {
    str(i): {
        "estado": "libre", # libre, preparando, pendiente_pago, pagado
        "items_actuales": [],
        "historial": []
    } for i in range(1, 41)
}

# Carta global de bebidas (editable desde el panel de admin)
carta_items = [
    { id: 1, categoria: "Cocktails", nombre: "Fernet 100", desc: "Fernet Branca con Coca-Cola tirada bien helada.", precio: 7000 },
    { id: 2, categoria: "Cocktails", nombre: "Gin Tonic 100", desc: "Gin artesanal, agua tónica premium, rodaja de limón.", precio: 7500 },
    { id: 3, categoria: "Cocktails", nombre: "Vodka con Speed / Naranja", desc: "Vodka importado con energizante o jugo cítrico.", precio: 7500 },
    { id: 4, categoria: "Cocktails", nombre: "Campari Orange", desc: "Campari con jugo de naranja exprimido y hielo.", precio: 7200 },
    { id: 5, categoria: "Cocktails", nombre: "Ron con Cola", desc: "Ron añejo con Coca-Cola y lima.", precio: 7000 },
    { id: 6, categoria: "Cocktails", nombre: "Daiquiri de Frutilla / Durazno", desc: "Ron, pulpa de fruta natural, lima y azúcar.", precio: 7800 },
    { id: 7, categoria: "Cocktails", nombre: "Mojito Tradicional", desc: "Ron blanco, menta fresca, lima, azúcar mascabo y soda.", precio: 7800 },
    { id: 8, categoria: "Cocktails", nombre: "Mulberry Spritz", desc: "Espumante, cordial de frutos rojos y agua tónica.", precio: 8000 },
    { id: 9, categoria: "Cocktails", nombre: "Yorkers Vibes", desc: "Bourbon, reducción de frutas de estación y cítricos.", precio: 8500 },
    { id: 10, categoria: "Cocktails", nombre: "Gangsta Tape", desc: "Trago de autor fuerte a base de ron especiado y jengibre.", precio: 8500 },
    { id: 11, categoria: "Cocktails", nombre: "100 Night Passion", desc: "Gin, maracuyá, almíbar especiado y toque de lima.", precio: 8500 },
    { id: 12, categoria: "Vinos & Espumantes", nombre: "Champagne Extra Brut", desc: "Botella 750ml ideal para brindar en la noche.", precio: 22000 },
    { id: 13, categoria: "Vinos & Espumantes", nombre: "Vino Tinto Malbec (Copa)", desc: "Copa de vino seleccionado de alta gama.", precio: 6000 },
    { id: 14, categoria: "Vinos & Espumantes", nombre: "Vino Blanco Chardonnay (Copa)", desc: "Copa de vino blanco fresco y frutado.", precio: 6000 },
    { id: 15, categoria: "Cervezas", nombre: "Cerveza Corona (Línea)", desc: "Botella 330ml con limón.", precio: 5500 },
    { id: 16, categoria: "Cervezas", nombre: "Cerveza Patagonia Amber Lager", desc: "Pinta tirada artesanal.", precio: 5800 },
    { id: 17, categoria: "Cervezas", nombre: "Cerveza Patagonia 24.7 (IPA)", desc: "Pinta tirada IPA refrescante y lupulada.", precio: 5800 },
    { id: 18, categoria: "Sin Alcohol", nombre: "Agua Mineral / Saborizada", desc: "500ml sin gas o con gas.", precio: 3000 },
    { id: 19, categoria: "Sin Alcohol", nombre: "Bebida Energizante Speed", desc: "Lata 250ml.", precio: 4500 },
    { id: 20, categoria: "Sin Alcohol", nombre: "Gaseosa Línea Pepsi / 7Up", desc: "Lata 350ml bien fría.", precio: 3500 }
]

@app.route('/')
def menu():
    return render_template('menu.html', items=carta_items)

@app.route('/api/carta')
def api_carta():
    return jsonify(carta_items)

@app.route('/caja')
def caja():
    return render_template('caja.html', mesas=mesas_estado)

# --- RUTAS DE ADMINISTRACIÓN ---

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('pin') == PIN_ADMIN:
            session['admin_logged'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error="Clave de administrador incorrecta")
    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    return render_template('admin_panel.html', items=carta_items)

@app.route('/admin/actualizar-precio', methods=['POST'])
def admin_actualizar_precio():
    if not session.get('admin_logged'):
        return jsonify({"success": False}), 403
    
    data = request.get_json()
    item_id = int(data.get('id'))
    nuevo_precio = int(data.get('precio'))
    
    for item in carta_items:
        if item['id'] == item_id:
            item['precio'] = nuevo_precio
            return jsonify({"success": True})
            
    return jsonify({"success": False}), 404

@app.route('/admin/agregar-item', methods=['POST'])
def admin_agregar_item():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_panel'))
    
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    desc = request.form.get('desc')
    precio = int(request.form.get('precio'))
    
    nuevo_id = max([i['id'] for i in carta_items], default=0) + 1
    carta_items.append({
        "id": nuevo_id,
        "categoria": categoria,
        "nombre": nombre,
        "desc": desc,
        "precio": precio
    })
    return redirect(url_for('admin_panel'))

@app.route('/admin/subir-excel', methods=['POST'])
def admin_subir_excel():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_panel'))
    
    if 'archivo_excel' in request.files:
        file = request.files['archivo_excel']
        if file.filename != '':
            try:
                # Lee el Excel con pandas. Espera columnas: categoria, nombre, desc, precio
                df = pd.read_excel(file)
                nuevos_items = []
                for index, row in df.iterrows():
                    nuevos_items.append({
                        "id": index + 1,
                        "categoria": str(row['categoria']),
                        "nombre": str(row['nombre']),
                        "desc": str(row['desc']),
                        "precio": int(row['precio'])
                    })
                global carta_items
                carta_items = nuevos_items
            except Exception as e:
                print("Error al procesar excel:", e)
                
    return redirect(url_for('admin_panel'))

# --- APIs DE PEDIDOS Y MESAS ---

@app.route('/api/verificar-pin', methods=['POST'])
def verificar_pin():
    data = request.get_json()
    if data.get('pin') == PIN_NOCHE:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route('/api/pedido', methods=['POST'])
def recibir_pedido():
    data = request.get_json()
    mesa = str(data.get('mesa'))
    items = data.get('items')
    
    if mesa in mesas_estado:
        mesas_estado[mesa]["estado"] = "preparando"
        nuevo_pedido = { "items": items, "estado_pago": "pendiente" }
        mesas_estado[mesa]["items_actuales"].append(nuevo_pedido)
        mesas_estado[mesa]["historial"].append({"tipo": "nuevo_pedido", "detalle": items})
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/cambiar-estado/<mesa>', methods=['POST'])
def cambiar_estado(mesa):
    data = request.get_json()
    nuevo_estado = data.get('estado')
    if mesa in mesas_estado:
        mesas_estado[mesa]["estado"] = nuevo_estado
        if nuevo_estado == "pagado":
            mesas_estado[mesa]["historial"].append({"tipo": "pago_confirmado", "detalle": "Mesa cerrada y pagada"})
            mesas_estado[mesa]["items_actuales"] = []
            mesas_estado[mesa]["estado"] = "libre"
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/liberar/<mesa>', methods=['POST'])
def liberar_mesa(mesa):
    if mesa in mesas_estado:
        mesas_estado[mesa]["items_actuales"] = []
        mesas_estado[mesa]["estado"] = "libre"
        mesas_estado[mesa]["historial"].append({"tipo": "liberacion", "detalle": "Mesa liberada manualmente"})
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)