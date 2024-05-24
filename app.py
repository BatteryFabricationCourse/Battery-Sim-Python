# app.py
from flask import Flask, request, jsonify
import pybamm

app = Flask(__name__)

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    chemistry = data.get('chemistry', 'lithium_ion')
    # Set up PyBAMM model
    if chemistry == 'lithium_ion':
        model = pybamm.lithium_ion.DFN()
    elif chemistry == 'lead_acid':
        model = pybamm.lead_acid.Full()
    else:
        return jsonify({'error': 'Unsupported chemistry'}), 400

    # Create simulation
    sim = pybamm.Simulation(model)
    sim.solve([0, 3600])  # Simulate for one hour

    # Extract results
    time = sim.solution["Time [s]"].entries
    voltage = sim.solution["Terminal voltage [V]"].entries

    return jsonify({'time': time.tolist(), 'voltage': voltage.tolist()})

if __name__ == '__main__':
    app.run(debug=True)
