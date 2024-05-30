# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import pybamm

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes
model = pybamm.lithium_ion.SPM()
batteries = {
    "NMC532": "Mohtat2020",
    "NCA": "NCA_Kim2011",
    "LFP":"Prada2013",
    "LG M50": "OKane2022"
}

@app.route('/simulate-lab1', methods=['POST'])
def simulate():
    print("New Request: ", request.json)
    data = request.json
    battery_type = data.get('Type')
    temperature = data.get('Ambient temperature [K]')
    capacity = data.get("Nominal cell capacity [A.h]")
    PosElectrodeThickness = data.get("Positive electrode thickness [m]")
    c_rates = data.get("C Rates")
    # Set up PyBAMM model
    if battery_type not in batteries.keys():
        return jsonify({'error': 'Unsupported chemistry'}), 400

    print("Parameter Set Name: ", batteries.get(battery_type))
    parameters = pybamm.ParameterValues(batteries.get(battery_type))
    
    #if temperature != 273.15:
    #    parameters.update({'Ambient temperature [K]': float(temperature)})
    
    #if capacity != 0:
    #     parameters.update({"Nominal cell capacity [A.h]":capacity})
        
    #if PosElectrodeThickness != 0:
    #    parameters.update({"Positive electrode thickness [m]": PosElectrodeThickness})
    
    
    
    fast_solver = pybamm.CasadiSolver(mode="fast")
    
    experiment1_result = [{'title':'Charging at different C Rates'}]
    final_result = []
    exp1graphs = []
    if c_rates == None:
        c_rates = [1]
    
    for c_rate in c_rates:
        experiment = pybamm.Experiment(
            [f"Charge at {c_rate}C for 3 hours or until 4.3 V"]
        )
        sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment)
        print(f"Running simulation C Rate: {c_rate} charging\n")
        sol = sim.solve(initial_soc=0, solver=fast_solver)
        exp1graphs.append({"name": "Time [min]", "values":sol["Time [min]"].entries.tolist()})
        exp1graphs.append({"name": "Terminal voltage [V]", "fname":f"{c_rate}C", "values":sol["Terminal voltage [V]"].entries.tolist()})
        print(f"Simulation Success C Rate: {c_rate} charging\n")
    print("Experiment 1 Results: ", experiment1_result)

    experiment2_result = [{'title':'Discharging at different C Rates'}]
    exp2graphs = []
    for c_rate in c_rates:
        experiment = pybamm.Experiment(
            [f"Discharge at {c_rate}C for 3 hours or until 2.0 V"]
        )
        sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment)
        print(f"Running simulation C Rate: {c_rate} discharging\n")
        sol = sim.solve(initial_soc=1, solver=fast_solver)
        exp2graphs.append({"name": "Time [min]", "values":sol["Time [min]"].entries.tolist()})
        exp2graphs.append({"name": "Terminal voltage [V]", "fname":f"{c_rate}C", "values":sol["Terminal voltage [V]"].entries.tolist()})
        
    print("Experiment 2 Results: ", experiment2_result)
    
    experiment1_result.append({"graphs": exp1graphs})
    experiment2_result.append({"graphs": exp2graphs})
    final_result.append(experiment1_result)
    final_result.append(experiment2_result)
    
    result_json = jsonify(final_result)

    print("Request Answered: ", final_result)
    return result_json

if __name__ == '__main__':
    app.run()
    
def run_simulation(c_rate, charge=True):
    # Define the parameters
    
    param = pybamm.ParameterValues("NCA_Kim2011")
    
    
    param.update({"Lower voltage cut-off [V]": 1.8})
    param.update({"Upper voltage cut-off [V]": 4.5})
    experiment = None
    #t_eval = np.linspace(0, 3700 / c_rate, 500)  # Simulate for the appropriate time based on C-rate
    
    # Set the current function
    if charge:
        experiment = pybamm.Experiment(
            [f"Charge at {c_rate}C for 3 hours or until 4.3 V"]
        )
    else:
        experiment = pybamm.Experiment(
            [f"Discharge at {c_rate}C for 3 hours or until 2 V"]
        )
    
    # Set up the simulation
    sim = pybamm.Simulation(model, parameter_values=param, experiment=experiment)
    
    print(f"Running simulation c:{c_rate} charging:{charge}\n")
    
    fast_solver = pybamm.CasadiSolver(mode="fast")
    # Run the simulation
    if charge:
        sim.solve(initial_soc=0.0001, solver=fast_solver)
    else:
        sim.solve(initial_soc=0.99, solver=fast_solver)
    
    return sim.solution, "Charging" if charge else "Discharging"