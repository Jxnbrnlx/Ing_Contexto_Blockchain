from flask import Flask, jsonify, request, render_template
import hashlib
import json
from time import time

app = Flask(__name__)

# ==========================================
# LÓGICA DE LA BLOCKCHAIN
# ==========================================
class Blockchain:
    def __init__(self):
        self.chain = []
        # Crear el bloque génesis
        self.new_block(previous_hash='1', proof=100, lot_data={"mensaje": "Bloque Génesis - OrigenChain"})

    def new_block(self, proof, previous_hash=None, lot_data=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'lot_data': lot_data or {},
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        self.chain.append(block)
        return block

    @staticmethod
    def hash(block):
        # Hashea un bloque usando SHA-256
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

# Instanciar la blockchain
blockchain = Blockchain()

# Agregar un lote de ejemplo para demostración (OC-CAF-1042)
blockchain.new_block(
    proof=12345, 
    previous_hash=blockchain.hash(blockchain.last_block),
    lot_data={
        "id_lote": "OC-CAF-1042",
        "producto": "Café especial",
        "origen": "Pitalito, Huila",
        "cantidad": "180 kg",
        "responsable": "Asociación Cafetera El Roble",
        "estado": "Recepción confirmada"
    }
)

# ==========================================
# RUTAS DEL SERVIDOR WEB
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/resumen', methods=['GET'])
def get_resumen():
    total_lotes = len(blockchain.chain) - 1 # Sin contar el génesis
    total_bloques = len(blockchain.chain)
    return jsonify({
        'total_lotes': total_lotes,
        'total_bloques': total_bloques,
        'estado_red': 'Activo - Íntegro'
    }), 200

@app.route('/api/lotes', methods=['GET'])
def get_lotes():
    # Extraer solo la información de los lotes (omitiendo el bloque génesis)
    lotes = [block['lot_data'] for block in blockchain.chain[1:]]
    # Invertir para mostrar los más recientes primero
    return jsonify(list(reversed(lotes))), 200

@app.route('/api/lotes', methods=['POST'])
def register_lote():
    valores = request.get_json()
    
    # Validar que los campos requeridos estén en la petición
    requeridos = ['id_lote', 'producto', 'origen', 'cantidad', 'responsable']
    if not all(k in valores for k in requeridos):
        return jsonify({'error': 'Faltan valores en el formulario'}), 400

    # Crear el nuevo lote
    lot_data = {
        "id_lote": valores['id_lote'],
        "producto": valores['producto'],
        "origen": valores['origen'],
        "cantidad": valores['cantidad'] + " kg",
        "responsable": valores['responsable'],
        "estado": "Registrado"
    }

    last_block = blockchain.last_block
    # En una red real habría un proceso de "Prueba de Trabajo", aquí lo simplificamos
    proof = 12345 
    
    # Añadir el bloque a la cadena
    nuevo_bloque = blockchain.new_block(proof, blockchain.hash(last_block), lot_data)

    return jsonify({
        'mensaje': 'Lote registrado exitosamente en la Blockchain',
        'bloque_index': nuevo_bloque['index']
    }), 201

if __name__ == '__main__':
    app.run(debug=True, port=5000)