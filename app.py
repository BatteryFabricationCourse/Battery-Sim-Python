# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import pybamm

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

@app.route('/simulate', methods=['POST'])
def simulate():
    print("New Request: ", request.json)
    data = request.json
    chemistry = data.get('chemistry')
    temperature = data.get('temperature')
    
    # Set up PyBAMM model
    if chemistry == 'lithium_ion':
        model = pybamm.lithium_ion.DFN()
    elif chemistry == 'lead_acid':
        model = pybamm.lead_acid.Full()
    else:
        return jsonify({'error': 'Unsupported chemistry'}), 400

    parameters = pybamm.ParameterValues("Chen2020")
    
    parameters['Ambient temperature [K]'] = 273.15 + temperature
    parameters['Initial temperature [K]'] = 273.15 + temperature
    parameters
    # Create simulation
    sim = pybamm.Simulation(model, parameter_values=parameters)
    solution = sim.solve([0, 3600])  # Simulate for one hour
    # Extract results
    time = solution["Time [s]"].entries
    voltage = solution["Terminal voltage [V]"].entries
    

    print("Request Answered",jsonify({'time': time.tolist(), 'voltage': voltage.tolist()}))
    return jsonify({'time': time.tolist(), 'voltage': voltage.tolist()})

if __name__ == '__main__':
    app.run(debug=True)