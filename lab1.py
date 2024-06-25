from flask import jsonify
import pybamm
from utils import update_parameters, run_charging_experiments, run_cycling_experiment

model = pybamm.lithium_ion.SPM()
batteries = {
    "NMC": "Mohtat2020",
    "NCA": "NCA_Kim2011",
    "LFP": "Prada2013",
    "LG M50": "OKane2022",
    "Silicon": "Chen2020_composite",
}


def simulate_lab1(request):
    try:
        print("New Request: ", request.json)
        data = request.json
        battery_type = data.get("Type")
        temperature = data.get("Ambient temperature [K]")
        capacity = data.get("Nominal cell capacity [A.h]")
        PosElectrodeThickness = data.get("Positive electrode thickness [m]")
        c_rates = data.get("C Rates", [1])
        cycles = data.get("Cycles", 1)

        if cycles > 100:
            cycles = 100

        if battery_type not in batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = pybamm.ParameterValues(batteries[battery_type])
        update_parameters(parameters, temperature, capacity, None, None)

        fast_solver = pybamm.CasadiSolver()

        final_result = []
        final_result.append(
            run_charging_experiments(c_rates, "Charge", model, parameters, fast_solver)
        )
        final_result.append(
            run_charging_experiments(
                c_rates, "Discharge", model, parameters, fast_solver
            )
        )
        final_result.append(run_cycling_experiment(cycles, model, parameters))

        print("Request Answered: ", final_result)
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
