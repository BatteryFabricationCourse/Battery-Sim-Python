from flask import Flask, request, jsonify
import pybamm
import numpy as np
import scilicon_anode

app = Flask(__name__)

# Define the model and battery parameters
model = pybamm.lithium_ion.SPM()
batteries = {
    "NMC532": "Mohtat2020", # "Nominal cell capacity [A.h]": 5.0
    "NCA": "NCA_Kim2011", # "Nominal cell capacity [A.h]": 0.43
    "LFP": "Prada2013", # "Nominal cell capacity [A.h]": 2.3,
    "LG M50": "OKane2022", # "Nominal cell capacity [A.h]": 5.0,
}



@app.errorhandler(404)
def page_not_found(e):
    return jsonify(["ERROR: " + str(e)])

@app.route("/")
def home():
    return "Welp, at least the home page works."

@app.route("/simulate-lab1", methods=["POST"])
def simulate():
    try:
        print("New Request: ", request.json)
        data = request.json
        battery_type = data.get("Type")
        temperature = data.get("Ambient temperature [K]")
        capacity = data.get("Nominal cell capacity [A.h]")
        PosElectrodeThickness = data.get("Positive electrode thickness [m]")
        c_rates = data.get("C Rates", [1])
        cycles = data.get("Cycles", 1)
        use_scilicon = data.get("Silicon Percentage")
        if battery_type not in batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = pybamm.ParameterValues(batteries[battery_type])
        update_parameters(parameters, temperature, capacity, PosElectrodeThickness, use_scilicon)

        fast_solver = pybamm.CasadiSolver(mode="safe")

        final_result = []
        final_result.append(run_experiment(c_rates, "Charge", model, parameters, fast_solver))
        final_result.append(run_experiment(c_rates, "Discharge", model, parameters, fast_solver))
        final_result.append(run_cycling_experiment(cycles, model, parameters))

        print("Request Answered: ", final_result)
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])

def update_parameters(parameters, temperature, capacity, PosElectrodeThickness, use_scilicon):
    if temperature and temperature != 0:
        parameters.update({"Ambient temperature [K]": float(temperature)})
    if capacity and capacity != 0:
        parameters.update({"Nominal cell capacity [A.h]": capacity})
    if PosElectrodeThickness and PosElectrodeThickness != 0:
        parameters.update({"Positive electrode thickness [m]": PosElectrodeThickness})
    if use_scilicon == 1:
        #for parameter in scilicon_anode.scilicon_anode_parameters:
            #print(parameter)
        parameters.update(scilicon_anode.scilicon_anode_parameters, check_already_exists=False)

def run_experiment(c_rates, mode, model, parameters, solver):
    experiment_result = [{"title": f"{mode.capitalize()}ing at different C Rates"}]
    graphs = []
    y_axis_label = None
    for c_rate in c_rates:
        if mode == "Charge":
            experiment = pybamm.Experiment([f"Charge at {c_rate}C for 3 hours or until 4.3 V"])
            initial_soc = 0
            y_axis_label = 'Throughput capacity [A.h]'
        else:
            experiment = pybamm.Experiment([f"Discharge at {c_rate}C for 300 hours or until 2.0 V"])
            initial_soc = 1
            y_axis_label= 'Discharge capacity [A.h]'

        sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment)
        print(f"Running simulation C Rate: {c_rate} {mode.lower()}ing\n")
        sol = sim.solve(initial_soc=initial_soc, solver=solver)
        print(sol["Total lithium [mol]"])
        graphs.append({"name": y_axis_label, "values": sol[y_axis_label].entries.tolist()})
        graphs.append({"name": "Voltage [V]", "fname": f"{c_rate}C", "values": sol["Total lithium [mol]"].entries.tolist()})
        #graphs.append({"name": "Total lithium [mol]", "fname": f"{c_rate}C", "values": sol["Total lithium [mol]"].entries.tolist()})

    experiment_result.append({"graphs": graphs})
    return experiment_result

def run_cycling_experiment(cycles, model, parameters):
    experiment_result = [{"title": "Cycling"}]
    graphs = []
    experiment = pybamm.Experiment([("Charge at 1 C until 4.0 V", "Hold at 4.0 V until C/10", "Rest for 5 minutes",
                                     "Discharge at 1 C until 2.2 V", "Rest for 5 minutes")] * cycles)
    sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment)
    print("Running simulation Cycling\n")
    solver = pybamm.CasadiSolver("fast", dt_max=100000)
    sol = sim.solve(solver=solver)

    graphs.append({"name": "Time [h]", "values": average_array(sol["Time [h]"].entries.tolist())})
    graphs.append({"name": "Discharge capacity [A.h]", "fname": "Capacity",
                   "values": average_array(sol["Discharge capacity [A.h]"].entries.tolist())})

    experiment_result.append({"graphs": graphs})
    return experiment_result

def average_array(a):
    averaged_array = []
    n_averaged_elements = max(1, len(a) // 100)
    for i in range(0, len(a), n_averaged_elements):
        averaged_array.append(np.mean(a[i:i + n_averaged_elements]))
    return averaged_array

if __name__ == "__main__":
    app.run(debug=True)
