from flask import Flask, render_template, request, jsonify, session
import os
from datetime import datetime

app = Flask(__name__)
# Necesario para manejar sesiones seguras del PIN en el navegador del cliente
app.secret_key = 'clave_secreta_boliche_100_secure'

# Generar un PIN aleatorio para las mesas que cambia (puedes cambiarlo manualmente o dejar este fijo por noche)
PIN_NOCHE_ACTUAL = "7420" 

# Estructura de las 40 mesas del boliche
mesas = {}
for i in range(1, 41):
    mesas[str(i)] = {
        "estado": "verde",  # verde (libre), rojo (pedido nuevo), amarillo (abierta/en proceso)
        "items": [],
        "total": 0,
        "historial_consumos": []
    }

# Simulación de la carta de bebidas del boliche "100"
bebidas = [
    {"id": 1, "nombre": "Fernet con Coca", "precio": 6500, "categoria": "Tragos"},
    {"id": 2, "nombre": "Gin Tonic", "precio": 7000, "categoria": "Tragos"},
    {"id": 3, "nombre": "Vodka con Speed", "precio": 7500, "categoria": "Tragos"},
    {"id": 4, "nombre": "Cerveza Corona", "precio": 4500, "categoria": "Cervezas"},
    {"id": 5, "nombre": "Latita de Red Bull", "precio": 4000, "categoria": "Energizantes"},
    {"id": 6, "nombre": "Agua Mineral", "precio": 2500, "categoria": "Sin Alcohol"}
]

@app.route('/')
def menu():
    mesa = request.args.get('mesa', '1')
    return render_template('menu.html', bebidas=bebidas, mesa=mesa)

@app.route('/verificar_pin', methods=['POST'])
def verificar_pin():
    data = request.json
    pin_ingresado = data.get('pin')
    if pin_ingresado == PIN_NOCHE_ACTUAL:
        session['pin_validado'] = True
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "mensaje": "PIN incorrecto. Solicítalo al personal del boliche."}), 401

@app.route('/enviar_pedido', methods=['POST'])
def enviar_pedido():
    # Validar que el cliente haya ingresado el PIN de la mesa
    if not session.get('pin_validado'):
        return jsonify({"status": "error", "mensaje": "Sesión no autorizada. Debe ingresar el PIN de la mesa."}), 401

    data = request.json
    num_mesa = str(data.get('mesa'))
    items = data.get('items', [])

    if num_mesa not in mesas:
        return jsonify({"status": "error", "mensaje": "Mesa inválida"}), 400

    subtotal_nuevo = sum(item['precio'] * item['cantidad'] for item in items)

    # Agregar los ítems al pedido actual de la mesa y cambiar estado a ROJO (nuevo pedido)
    mesas[num_mesa]["items"].extend(items)
    mesas[num_mesa]["total"] += subtotal_nuevo
    mesas[num_mesa]["estado"] = "rojo"

    return jsonify({"status": "success"})

@app.route('/caja')
def caja():
    return render_template('caja.html')

@app.route('/api/mesas')
def api_mesas():
    return jsonify(mesas)

@app.route('/aceptar_pedido/<num_mesa>', methods=['POST'])
def aceptar_pedido(num_mesa):
    if num_mesa in mesas:
        mesas[num_mesa]["estado"] = "amarillo" # Pasa a proceso / en atención
    return jsonify({"status": "success"})

@app.route('/cobrar_mesa/<num_mesa>', methods=['POST'])
def cobrar_mesa(num_mesa):
    if num_mesa in mesas and mesas[num_mesa]["total"] > 0:
        hora_actual = datetime.now().strftime("%H:%M")
        registro = {
            "hora": hora_actual,
            "items": list(mesas[num_mesa]["items"]),
            "total": mesas[num_mesa]["total"]
        }
        # Guardar en el historial de la noche y limpiar la mesa para el próximo grupo
        mesas[num_mesa]["historial_consumos"].append(registro)
        mesas[num_mesa]["items"] = []
        mesas[num_mesa]["total"] = 0
        mesas[num_mesa]["estado"] = "verde"
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Render asigna automáticamente el puerto mediante la variable de entorno PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)