from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# PIN temporal de seguridad de la noche
PIN_NOCHE = "7420"

# Estructura para las 40 mesas: 
# Cada mesa almacena su estado actual, la lista de pedidos activos y el historial de toda la noche.
mesas_estado = {
    str(i): {
        "estado": "libre", # libre, preparando, pendiente_pago, pagado
        "items_actuales": [],
        "historial": []
    } for i in range(1, 41)
}

@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/caja')
def caja():
    return render_template('caja.html', mesas=mesas_estado)

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
        # Al entrar un nuevo pedido, pasa a estado "preparando" (Rojo)
        mesas_estado[mesa]["estado"] = "preparando"
        
        # Agregamos metadatos al pedido
        nuevo_pedido = {
            "items": items,
            "estado_pago": "pendiente"
        }
        mesas_estado[mesa]["items_actuales"].append(nuevo_pedido)
        mesas_estado[mesa]["historial"].append({"tipo": "nuevo_pedido", "detalle": items})
        
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/cambiar-estado/<mesa>', methods=['POST'])
def cambiar_estado(mesa):
    data = request.get_json()
    nuevo_estado = data.get('estado') # preparando, pendiente_pago, pagado
    
    if mesa in mesas_estado:
        mesas_estado[mesa]["estado"] = nuevo_estado
        if nuevo_estado == "pagado":
            # Guardamos en el historial que se pagó y limpiamos la mesa para liberar
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