from flask import jsonify
import pybamm
import numpy
from scipy.ndimage import interpolation
import utils

batteries = {
    "NMC": "Mohtat2020",
    "NCA": "NCA_Kim2011",
    "LFP": "Prada2013",
    "LG M50": "OKane2022",
    "Silicon": "Chen2020_composite",
}


def simulate_lab3(request):
    try:
        print("New Request: ", request.json)
        data = request.json
        battery_type = data.get("Type")
        temperature = data.get("Ambient temperature [K]")

        charging_properties = data.get("Charging Properties")
        charge_current = charging_properties.get("Charge C", 1)
        charge_voltage = charging_properties.get("Charge V", 1)
        hold_voltage = charging_properties.get("Hold V", 1)
        hold_current = charging_properties.get("Hold C", 1)
        rest1_minutes = charging_properties.get("Rest T", 1)
        discharge_current = charging_properties.get("Discharge C", 1)
        discharge_voltage = charging_properties.get("Discharge V", 1)
        rest2_minutes = charging_properties.get("Rest 2T", 1)
        cycles = charging_properties.get("Cycles", 1)

        if cycles > 50:
            cycles = 50

        if battery_type not in batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = pybamm.ParameterValues(batteries[battery_type])
        utils.update_parameters(parameters, temperature, None, None, None)

        final_result = []
        graphs = []
        experiment = pybamm.Experiment(
            [
                (
                    f"Charge at {charge_current} C until {charge_voltage} V",
                    f"Hold at {hold_voltage} V until C*{hold_current}",
                    f"Rest for {rest1_minutes} minutes",
                    f"Discharge at {discharge_current} C until {discharge_voltage} V",
                    f"Rest for {rest2_minutes} minutes",
                )
            ]
            * cycles
        )
        model = model = pybamm.lithium_ion.SPM()
        if battery_type != "LFP":
            model = pybamm.lithium_ion.SPM({"SEI": "ec reaction limited"})
            parameters.update({"SEI kinetic rate constant [m.s-1]": 1e-14})
        
        
        sim = pybamm.Simulation(
            model, parameter_values=parameters, experiment=experiment
        )
        print("Running simulation Cycling\n")
        solver = pybamm.CasadiSolver("fast", dt_max=10000)
        sol = sim.solve(solver=solver, save_at_cycles=1, initial_soc=0.1)

        
        # Prepare data for plotting
        experiment_result = [{"title": "Capacity over Cycles"}]
        graphs.append(
            {
                "name": "Cycle",
                "values": sol.summary_variables["Cycle number"].tolist(),
            }
        )
        graphs.append(
            {
                "name": "Capacity [A.h]",
                "fname": "Capacity",
                "values": sol.summary_variables["Capacity [A.h]"].tolist(),
            }
        )
        experiment_result.append({"graphs": graphs})
        final_result.append(experiment_result)

        experiment_result = [{"title": "Voltage over Cycles"}]
        
        experiment_result.append({"graphs": utils.plot_against_cycle(sol, cycles, "Voltage [V]", "Voltage")})
        final_result.append(experiment_result)

        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
