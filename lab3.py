from flask import jsonify
import pybamm
import numpy as np
from scipy.ndimage import interpolation
import utils

# Add voltage limit for lfp 3.65, 2.5, NMC 4.2, 3, NCA, 4.3, 2.5
# Keep hold at same voltage
#Add Capacity Label
# Charge and discharge against Capacity for 1st and last cycle

def simulate_lab3(request):
    try:
        print("New Request: ", request.json)
        data: dict = request.json
        battery_type: str = data.get("Type")
        temperature: float = data.get("Ambient temperature [K]")

        charging_properties: dict = data.get("Charging Properties")
        charge_current: float = charging_properties.get("Charge C", 1)
        charge_voltage: float = charging_properties.get("Charge V", 1)
        hold_voltage: float = charging_properties.get("Hold V", 1)
        hold_current: float = charging_properties.get("Hold C", 1)
        rest1_minutes: float = charging_properties.get("Rest T", 1)
        discharge_current: float = charging_properties.get("Discharge C", 1)
        discharge_voltage: float = charging_properties.get("Discharge V", 1)
        rest2_minutes: float = charging_properties.get("Rest 2T", 1)
        cycles: float = charging_properties.get("Cycles", 1)

        if battery_type not in utils.batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = utils.get_battery_parameters(
            battery_type, degradation_enabled=True
        )

        if cycles > 50:
            cycles = 50

        utils.update_parameters(parameters, temperature, None, None, None)

        model = pybamm.lithium_ion.SPM({"SEI": "ec reaction limited"})

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

        sim = pybamm.Simulation(
            model, parameter_values=parameters, experiment=experiment
        )
        print("Running simulation Cycling\n")
        solver = pybamm.CasadiSolver("safe", dt_max=0.01)
        sol = sim.solve(solver=solver, save_at_cycles=1, initial_soc=0.01)

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

        experiment_result.append(
            {"graphs": utils.plot_against_cycle(sol, cycles, "Voltage [V]", "Voltage")}
        )
        final_result.append(experiment_result)

        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])