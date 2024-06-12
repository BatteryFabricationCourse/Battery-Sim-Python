from flask import Flask, request, jsonify
import pybamm
import numpy as np
import os
from OpenSSL import SSL


context = SSL.Context(SSL.TLSv1_2_METHOD)
context.use_privatekey_file('server.key')
context.use_certificate_file('server.crt') 

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

model = pybamm.lithium_ion.SPM()
batteries = {
    "NMC532": "Mohtat2020",
    "NCA": "NCA_Kim2011",
    "LFP": "Prada2013",
    "LG M50": "OKane2022"
}

@app.errorhandler(404)
def page_not_found(e):
    return jsonify(["ERROR: " + str(e)])

@app.route("/")
def home():
    return "Welp, at least the home page works."

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

        if battery_type not in batteries.keys():
            return jsonify({'error': 'Unsupported chemistry'}), 400

        parameters = pybamm.ParameterValues(batteries.get(battery_type))

        if temperature is not None and temperature != 0:
            parameters.update({'Ambient temperature [K]': float(temperature)})

        if capacity is not None and capacity != 0:
            parameters.update({"Nominal cell capacity [A.h]": capacity})

        if PosElectrodeThickness is not None and PosElectrodeThickness != 0:
            parameters.update({"Positive electrode thickness [m]": PosElectrodeThickness})

        if cycles is None or cycles == 0:
            cycles = 1

        fast_solver = pybamm.CasadiSolver(mode="safe without grid")

        experiment1_result = [{'title':'Charging at different C Rates'}]
        final_result = []
        exp1graphs = []
        if c_rates is None:
            c_rates = [1]

        for c_rate in c_rates:
            experiment1 = pybamm.Experiment([f"Charge at {c_rate}C for 3 hours or until 4.3 V"])
            sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment1)
            print(f"Running simulation C Rate: {c_rate} charging\n")
            sol = sim.solve(initial_soc=0, solver=fast_solver)

            exp1graphs.append({"name": "Throughput capacity [A.h]", "values": sol["Throughput capacity [A.h]"].entries.tolist()})
            exp1graphs.append({"name": "Voltage [V]", "fname": f"{c_rate}C", "values": sol["Voltage [V]"].entries.tolist()})

        experiment1_result.append({"graphs": exp1graphs})
        final_result.append(experiment1_result)

        del exp1graphs
        del experiment1_result
        del sim
        del sol

        experiment2_result = [{'title':'Discharging at different C Rates'}]
        exp2graphs = []
        for c_rate in c_rates:
            experiment2 = pybamm.Experiment([f"Discharge at {c_rate}C for 300 hours or until 2.0 V"])
            sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment2)
            print(f"Running simulation C Rate: {c_rate} discharging\n")
            sol = sim.solve(initial_soc=1, solver=fast_solver)

            exp2graphs.append({"name": "Discharge capacity [A.h]", "values": sol["Discharge capacity [A.h]"].entries.tolist()})
            exp2graphs.append({"name": "Voltage [V]", "fname": f"{c_rate}C", "values": sol["Voltage [V]"].entries.tolist()})

        experiment2_result.append({"graphs": exp2graphs})
        final_result.append(experiment2_result)

        del exp2graphs
        del experiment2_result
        del sim
        del sol

        experiment3_result = [{'title':'Cycling'}]
        exp3graphs = []
        experiment3 = pybamm.Experiment([
            (
                "Charge at 1 C until 4.0 V",
                "Hold at 4.0 V until C/10",
                "Rest for 5 minutes",
                "Discharge at 1 C until 2.2 V",
                "Rest for 5 minutes",
            )
        ] * cycles)
        sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment3)
        print(f"Running simulation Cycling\n")
        solver = pybamm.CasadiSolver("fast", dt_max=100000)
        sol = sim.solve(solver=solver)
        exp3graphs.append({"name": "Time [h]", "values": average_array(sol["Time [h]"].entries.tolist())})
        exp3graphs.append({"name": "Discharge capacity [A.h]", "fname": f"Capacity", "values": average_array(sol["Discharge capacity [A.h]"].entries.tolist())})

        experiment3_result.append({"graphs": exp3graphs})
        final_result.append(experiment3_result)

        del exp3graphs
        del experiment3_result
        del sim
        del sol

        result_json = jsonify(final_result)

        print("Request Answered: ", final_result)
        return result_json

    except Exception as e:
        err_json = jsonify(["ERROR: " + str(e)])
        return err_json

def average_array(a):
    averaged_array = []
    n_averaged_elements = int(len(a) / 100)
    for i in range(0, len(a), n_averaged_elements):
        slice_from_index = i
        slice_to_index = slice_from_index + n_averaged_elements
        averaged_array.append(np.mean(a[slice_from_index:slice_to_index]))

    return averaged_array

if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True, ssl_context=context)
