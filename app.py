from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Hello World"})

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({"data": "This is some sample data"})

if __name__ == '__main__':
    app.run(debug=True)
