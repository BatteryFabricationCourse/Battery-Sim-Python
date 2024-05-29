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
    # Create simulation
    sim = pybamm.Simulation(model, parameter_values=parameters)
    solution = sim.solve([0, 3600])  # Simulate for one hour
    # Extract results
    time = solution["Time [h]"].entries
    voltage = solution["Terminal voltage [V]"].entries
    
    result = [{'title':'Battery Terminal Voltage Over Time'},{'name': "Time [h]", 'values': time.tolist()},{ 'name':'Terminal voltage [V]', 'values': voltage.tolist()}]
    
    result_json = jsonify(result)

    print("Request Answered: ", result)
    return result_json

if __name__ == '__main__':
    app.run()