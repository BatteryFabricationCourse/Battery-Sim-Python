# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import pybamm
import numpy as np
app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes
model = pybamm.lithium_ion.SPM(
)
batteries = {
    "NMC532": "Mohtat2020",
    "NCA": "NCA_Kim2011",
    "LFP":"Prada2013",
    "LG M50": "OKane2022"
}

@app.route('/simulate-lab1', methods=['POST'])
def simulate():
    try:
        print("New Request: ", request.json)
        data = request.json
        battery_type = data.get('Type')
        temperature = data.get('Ambient temperature [K]')
        capacity = data.get("Nominal cell capacity [A.h]")
        PosElectrodeThickness = data.get("Positive electrode thickness [m]")
        c_rates = data.get("C Rates")
        cycles = data.get("Cycles")
        
        # Set up PyBAMM model
        if battery_type not in batteries.keys():
            return jsonify({'error': 'Unsupported chemistry'}), 400

        print("Parameter Set Name: ", batteries.get(battery_type))
        parameters = pybamm.ParameterValues(batteries.get(battery_type))
        
        if temperature is not None:
            if temperature != 0:
                parameters.update({'Ambient temperature [K]': float(temperature)})
        
        if capacity is not None:
            if capacity != 0:
                parameters.update({"Nominal cell capacity [A.h]":capacity})
        
        if PosElectrodeThickness is not None:    
            if PosElectrodeThickness != 0:
                parameters.update({"Positive electrode thickness [m]": PosElectrodeThickness})
        if cycles is None or cycles == 0:
            cycles = 2
        
        
        fast_solver = pybamm.CasadiSolver(mode="safe without grid")
        
        experiment1_result = [{'title':'Charging at different C Rates'}]
        final_result = []
        exp1graphs = []
        if c_rates == None:
            c_rates = [1]
        
        for c_rate in c_rates:
            experiment1 = pybamm.Experiment(
                [f"Charge at {c_rate}C for 3 hours or until 4.3 V"]
            )
            sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment1)
            print(f"Running simulation C Rate: {c_rate} charging\n")
            sol = sim.solve(initial_soc=0, solver=fast_solver)
            
            exp1graphs.append({"name": "Throughput capacity [A.h]", "values":sol["Throughput capacity [A.h]"].entries.tolist()})
            exp1graphs.append({"name": "Voltage [V]", "fname":f"{c_rate}C", "values":sol["Voltage [V]"].entries.tolist()})
        
        experiment1_result.append({"graphs": exp1graphs})
        final_result.append(experiment1_result)
        
        del exp1graphs
        del experiment1_result
        del sim
        del sol
        

        experiment2_result = [{'title':'Discharging at different C Rates'}]
        exp2graphs = []
        for c_rate in c_rates:
            experiment2 = pybamm.Experiment(
                [f"Discharge at {c_rate}C for 3 hours or until 2.0 V"]
            )
            sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment2)
            print(f"Running simulation C Rate: {c_rate} discharging\n")
            sol = sim.solve(initial_soc=1, solver=fast_solver)
            
            exp2graphs.append({"name": "Discharge capacity [A.h]", "values":sol["Discharge capacity [A.h]"].entries.tolist()})
            exp2graphs.append({"name": "Voltage [V]", "fname":f"{c_rate}C", "values":sol["Voltage [V]"].entries.tolist()})
            
        experiment2_result.append({"graphs": exp2graphs})
        final_result.append(experiment2_result)
        
        del exp2graphs
        del experiment2_result
        del sim
        del sol
        
        experiment3_result = [{'title':'Cycling'}]
        exp3graphs = []
        experiment3 = pybamm.Experiment(
            [
        (
            "Charge at 1 C until 4.0 V",
            "Hold at 4.0 V until C/10",
            "Rest for 5 minutes",
            "Discharge at 1 C until 2.2 V",
            "Rest for 5 minutes",
        )
        ]
        * cycles
    #    + [
    #    (
    #        "Charge at 1 C until 4.0 V",
    #        "Hold at 4.0 V until C/20",
    #        "Rest for 30 minutes",
    #        "Discharge at C/3 until 2.2 V",
    #        "Rest for 30 minutes",
    #    ),
    #    (
    #        "Charge at 1 C until 4.0 V",
    #        "Hold at 4.0 V until C/20",
    #        "Rest for 30 minutes",
    #        "Discharge at 1 C until 2.2 V",
    #        "Rest for 30 minutes",
    #    ),
    #    (
    #        "Charge at 1 C until 4.0 V",
    #        "Hold at 4.0 V until C/20",
    #        "Rest for 30 minutes",
    #        "Discharge at 2 C until 2.2 V",
    #        "Rest for 30 minutes",
    #    ),
    #    (
    #        "Charge at 1 C until 4.0 V",
    #        "Hold at 4.0 V until C/20",
    #        "Rest for 30 minutes",
    #        pybamm.step.string("Discharge at 3 C until 2.2 V", period=10),
    #        "Rest for 30 minutes",
    #    ),
    #]
        )
        sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment3)
        print(f"Running simulation Cycling\n")
        solver = pybamm.CasadiSolver("fast", dt_max=100000)
        sol = sim.solve(solver=solver)
        exp3graphs.append({"name": "Time [h]", "values":average_array(sol["Time [h]"].entries.tolist())})
        #AhtomAh = average_array(np.multiply(sol["Total lithium capacity [A.h]"].entries,  10e-3), 100)
        exp3graphs.append({"name": "Discharge capacity [A.h]", "fname":f"Capacity", "values":average_array(sol["Discharge capacity [A.h]"].entries.tolist())})

        experiment3_result.append({"graphs": exp3graphs})
        final_result.append(experiment3_result)
        
        del exp3graphs
        del experiment3_result
        del sim
        del sol
        #del AhtomAh
        
        result_json = jsonify(final_result)

        print("Request Answered: ", final_result)
        return result_json

    except Exception as e:
        err_json = jsonify(["ERROR: " + str(e)])
        return err_json

if __name__ == '__main__':
    app.run()
    
def average_array(a):
    averaged_array = []
    n_averaged_elements = int(len(a) / 100)
    for i in range(0, len(a), n_averaged_elements):
        slice_from_index = i
        slice_to_index = slice_from_index + n_averaged_elements
        averaged_array.append(np.mean(a[slice_from_index:slice_to_index]))
        
    return averaged_array