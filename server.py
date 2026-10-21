import os
from flask import Flask, request, jsonify

app = Flask(__name__)

online_operators = {}

@app.route('/')
def index():
    return "TDT CLOUD SERVER IS RUNNING"

@app.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    op_id = data.get("operator_id", "UNKNOWN")
    online_operators[op_id] = {"ip": request.remote_addr, "status": "ONLINE"}
    return jsonify({"status": "SUCCESS", "operators": online_operators})

@app.route('/operators', methods=['GET'])
def get_operators():
    return jsonify(online_operators)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
  
