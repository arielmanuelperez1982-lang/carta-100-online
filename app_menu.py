from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import pandas as pd
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave_secreta_super_segura_100"

PIN_NOCHE = "7420"
PIN_ADMIN = "100admin"
DB_NAME = "base_100.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de Carta
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT,
            nombre TEXT,
            desc TEXT,
            precio INTEGER
        )
    ''')
    
    # Tabla de Mesas (Estado actual, items en formato texto/json, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mesas (
            numero TEXT PRIMARY KEY,
            estado TEXT,
            items_actuales TEXT,
            historial TEXT
        )
    ''')
    
    # Tabla de Historial de Ventas Diarias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas_diarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            mesa TEXT,
            detalle TEXT,
            total INTEGER,
            timestamp TEXT
        )
    ''')
    
    # Si la carta está vacía, insertamos la carta inicial por defecto
    cursor.execute('SELECT COUNT(*) FROM carta')
    if cursor.fetchone()[0] == 0:
        inicial_items = [
            ("Burbujas (Champagne & Espumantes)", "Chandon Extra Brut · Délice Rosé", "Tu primer brindis de la noche (Incluye 4 latas de Red Bull)", 90000),
            ("Burbujas (Champagne & Espumantes)", "Baron B Extra Brut", "Incluye 4 latas de Red Bull", 120000),
            ("Vodka (Botella)", "Belvedere", "Incluye 4 latas de Red Bull", 300000),
            ("Botellas (Bottle Service)", "Fernet Branca", "La mesa argentina - Más pedido 🔥 (Incluye 4 latas de Red Bull)", 180000),
            ("Clásicos", "Fernet Branca & Coke", "", 18000),
            ("Clásicos", "Aperol", "", 18000),
            ("Clásicos", "Negroni Carpano", "", 17000),
            ("Whisky (Botella)", "Jack Daniel's Nº7", "Apple · Fire · Honey", 250000),
            ("Cervezas", "Corona", "", 15000),
            ("Sin alcohol y mixers", "Red Bull", "Regular · Sugarfree · Pomelo Edition - Más pedido 🔥", 12000)
        ]
        cursor.executemany('INSERT INTO carta (categoria, nombre, desc, precio) VALUES (?, ?, ?, ?)', inicial_items)

    # Inicializar las 40 mesas si no existen
    for i in range(1, 41):
        mesa_num = str(i)
        cursor.execute('SELECT numero FROM mesas WHERE numero = ?', (mesa_num,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO mesas (numero, estado, items_actuales, historial) VALUES (?, ?, ?, ?)',
                           (mesa_num, 'libre', '[]', '[]'))
            
    conn.commit()
    conn.close()

# Inicializamos la base de datos al arrancar
init_db()

def get_carta():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM carta')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_mesas_estado():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM mesas')
    rows = cursor.fetchall()
    conn.close()
    
    mesas = {}
    import json
    for row in rows:
        mesas[row['numero']] = {
            "estado": row['estado'],
            "items_actuales": json.loads(row['items_actuales']),
            "historial": json.loads(row['historial'])
        }
    return mesas

@app.route('/')
def menu():
    return render_template('menu.html', items=get_carta())

@app.route('/api/carta')
def api_carta():
    return jsonify(get_carta())

@app.route('/caja')
def caja():
    return render_template('caja.html', mesas=get_mesas_estado())

# --- RUTAS DE ADMINISTRACIÓN ---

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('pin') == PIN_ADMIN:
            session['admin_logged'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error="Clave incorrecta")
    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    
    # Consultar ventas guardadas en la base de datos
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ventas_diarias ORDER BY id DESC LIMIT 100')
    ventas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return render_template('admin_panel.html', items=get_carta(), ventas=ventas)

@app.route('/admin/actualizar-precio', methods=['POST'])
def admin_actualizar_precio():
    if not session.get('admin_logged'):
        return jsonify({"success": False}), 403
    
    data = request.get_json()
    item_id = int(data.get('id'))
    nuevo_precio = int(data.get('precio'))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE carta SET precio = ? WHERE id = ?', (nuevo_precio, item_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/admin/agregar-item', methods=['POST'])
def admin_agregar_item():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_panel'))
    
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    desc = request.form.get('desc')
    precio = int(request.form.get('precio'))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO carta (categoria, nombre, desc, precio) VALUES (?, ?, ?, ?)',
                   (categoria, nombre, desc, precio))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/subir-excel', methods=['POST'])
def admin_subir_excel():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_panel'))
    
    if 'archivo_excel' in request.files:
        file = request.files['archivo_excel']
        if file.filename != '':
            try:
                df = pd.read_excel(file)
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                # Borramos la carta anterior para reemplazarla por la del Excel limpio
                cursor.execute('DELETE FROM carta')
                
                for _, row in df.iterrows():
                    cursor.execute('INSERT INTO carta (categoria, nombre, desc, precio) VALUES (?, ?, ?, ?)',
                                   (str(row['categoria']), str(row['nombre']), str(row['descripcion']), int(row['precio'])))
                conn.commit()
                conn.close()
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
    items = data.get('items') # Lista de productos solicitados
    
    mesas = get_mesas_estado()
    if mesa in mesas:
        import json
        estado_mesa = mesas[mesa]
        estado_mesa["estado"] = "preparando"
        
        nuevo_pedido = { "items": items, "estado_pago": "pendiente" }
        estado_mesa["items_actuales"].append(nuevo_pedido)
        estado_mesa["historial"].append({"tipo": "nuevo_pedido", "detalle": items, "hora": datetime.now().strftime("%H:%M:%S")})
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE mesas SET estado = ?, items_actuales = ?, historial = ? WHERE numero = ?',
                       (estado_mesa["estado"], json.dumps(estado_mesa["items_actuales"]), json.dumps(estado_mesa["historial"]), mesa))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/cambiar-estado/<mesa>', methods=['POST'])
def cambiar_estado(mesa):
    data = request.get_json()
    nuevo_estado = data.get('estado')
    
    mesas = get_mesas_estado()
    if mesa in mesas:
        import json
        estado_mesa = mesas[mesa]
        estado_mesa["estado"] = nuevo_estado
        
        if nuevo_estado == "pagado":
            # Calcular total de los ítems actuales para registrar venta diaria
            total_venta = 0
            for ped in estado_mesa["items_actuales"]:
                for itm in ped.get("items", []):
                    total_venta += int(itm.get('precio', 0)) * int(itm.get('cantidad', 1))
            
            # Registrar en ventas diarias
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            hora_actual = datetime.now().strftime("%H:%M:%S")
            detalle_str = f"Mesa {mesa} - Cerrada y Pagada"
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO ventas_diarias (fecha, mesa, detalle, total, timestamp) VALUES (?, ?, ?, ?, ?)',
                           (fecha_hoy, mesa, detalle_str, total_venta, hora_actual))
            
            # Limpiar mesa y pasar a libre
            estado_mesa["items_actuales"] = []
            estado_mesa["estado"] = "libre"
            estado_mesa["historial"].append({"tipo": "pago_confirmado", "detalle": f"Total cobrado: ${total_venta}", "hora": hora_actual})
        else:
            estado_mesa["historial"].append({"tipo": "cambio_estado", "detalle": f"Estado cambiado a {nuevo_estado}", "hora": datetime.now().strftime("%H:%M:%S")})
            
        cursor = sqlite3.connect(DB_NAME)
        cur = cursor.cursor()
        cur.execute('UPDATE mesas SET estado = ?, items_actuales = ?, historial = ? WHERE numero = ?',
                    (estado_mesa["estado"], json.dumps(estado_mesa["items_actuales"]), json.dumps(estado_mesa["historial"]), mesa))
        cursor.commit()
        cursor.close()
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/liberar/<mesa>', methods=['POST'])
def liberar_mesa(mesa):
    mesas = get_mesas_estado()
    if mesa in mesas:
        import json
        estado_mesa = mesas[mesa]
        estado_mesa["items_actuales"] = []
        estado_mesa["estado"] = "libre"
        estado_mesa["historial"].append({"tipo": "liberacion", "detalle": "Mesa liberada manualmente", "hora": datetime.now().strftime("%H:%M:%S")})
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE mesas SET estado = ?, items_actuales = ?, historial = ? WHERE numero = ?',
                       (estado_mesa["estado"], json.dumps(estado_mesa["items_actuales"]), json.dumps(estado_mesa["historial"]), mesa))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)