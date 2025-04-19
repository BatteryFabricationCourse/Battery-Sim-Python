from flask import Flask, request, jsonify
import flask_cors
from lab1 import simulate_lab1
from lab2 import simulate_lab2
from lab3 import simulate_lab3

app = Flask(__name__)
flask_cors.CORS(app)
app.config["PROPAGATE_EXCEPTIONS"] = True


@app.errorhandler(404)
def page_not_found(e):
    return jsonify(["ERROR: " + str(e)])


@app.route("/")
def home():
    return "Welp, at least the home page works."


@app.route("/simulate-lab1", methods=["POST"])
def simulate_lab1_route():
    return simulate_lab1(request)


@app.route("/simulate-lab2", methods=["POST"])
def simulate_lab2_route():
    return simulate_lab2(request)


@app.route("/simulate-lab3", methods=["POST"])
def simulate_lab3_route():
    return simulate_lab3(request)


@app.errorhandler(Exception)
def handle_exception(e):
    print(e)
    return jsonify(["ERROR: " + str(e)])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
