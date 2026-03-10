from flask import Flask
from flask_cors import CORS
from routes.prices import prices_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(prices_bp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)