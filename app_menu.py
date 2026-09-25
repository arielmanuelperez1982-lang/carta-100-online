from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# PIN temporal de seguridad de la noche
PIN_NOCHE = "7420"

# Estado temporal de las 40 mesas
mesas_estado = {str(i): [] for i in range(1, 41)}

@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/caja')
def caja():
    return render_template('caja.html', mesas=mesas_estado)

@app.route('/api/verificar-pin', methods=['POST'])
def verificar_pin():
    data = request.get_json()
    pin = data.get('pin')
    if pin == PIN_NOCHE:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route('/api/pedido', methods=['POST'])
def recibir_pedido():
    data = request.get_json()
    mesa = str(data.get('mesa'))
    items = data.get('items')
    
    if mesa in mesas_estado:
        mesas_estado[mesa].extend(items)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)