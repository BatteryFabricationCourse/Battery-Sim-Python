from flask import jsonify
import pybamm
import numpy as np
from scipy.ndimage import interpolation
import utils

# DONE Add voltage limit for lfp 3.65, 2.5, NMC 4.2, 3, NCA, 4.3, 2.5
# DONE Keep hold at same voltage
# DONE Add Capacity Label
# DONE Charge and discharge against Capacity for 1st and last cycle


def simulate_lab3(request):
    try:
        print("New Request: ", request.json)
        data: dict = request.json
        battery_type: str = data.get("Type")
        initial_charge: float = float(data.get("Initial SOC", 1)) * 0.01

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
        print("Initial Charge:", initial_charge)

        if battery_type not in utils.batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = utils.get_battery_parameters(
            battery_type, degradation_enabled=True
        )

        if cycles > 50:
            cycles = 50

        utils.update_parameters(parameters, None, 5, None, None, battery_type)

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
        sol = sim.solve(solver=solver, save_at_cycles=1, initial_soc=initial_charge)

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

        experiment_result = [{"title": "Charging in first and last cycle"}]

        graphs = []
        cycle1_charge, cycle1_discharge = utils.split_at_peak(
            sol.cycles[0]["Voltage [V]"].entries.tolist()
        )
        cycle1_crg_cap = sol.cycles[0]["Throughput capacity [A.h]"].entries.tolist()[
            : len(cycle1_charge)
        ]
        cycle1_dsc_cap = sol.cycles[0]["Throughput capacity [A.h]"].entries.tolist()[
            len(cycle1_charge) + 1 :
        ]

        cycle2_charge, cycle2_discharge = utils.split_at_peak(
            sol.cycles[len(sol.cycles) - 1]["Voltage [V]"].entries.tolist()
        )
        cycle2_crg_cap = sol.cycles[len(sol.cycles) - 1][
            "Throughput capacity [A.h]"
        ].entries.tolist()[: len(cycle2_charge)]

        cycle2_dsc_cap = sol.cycles[len(sol.cycles) - 1][
            "Throughput capacity [A.h]"
        ].entries.tolist()[len(cycle2_charge) + 1 :]

        graphs.append(
            {
                "name": "Throughput capacity [A.h]",
                "values": cycle1_crg_cap,
            }
        )
        graphs.append(
            {
                "name": "Voltage [V]",
                "fname": f"First",
                "values": cycle1_charge,
            }
        )

        graphs.append(
            {
                "name": "Throughput capacity [A.h]",
                "values": cycle2_crg_cap,
            }
        )
        graphs.append(
            {
                "name": "Voltage [V]",
                "fname": f"Last",
                "values": cycle2_charge,
            }
        )
        experiment_result.append({"graphs": graphs})

        final_result.append(experiment_result)

        experiment_result = [{"title": "discharge graphs"}]

        graphs = []

        graphs.append(
            {
                "name": "Throughput capacity [A.h]",
                "values": cycle1_dsc_cap,
            }
        )
        graphs.append(
            {
                "name": "Voltage [V]",
                "fname": f"First",
                "values": cycle1_discharge,
            }
        )

        graphs.append(
            {
                "name": "Throughput capacity [A.h]",
                "values": cycle2_dsc_cap,
            }
        )
        graphs.append(
            {
                "name": "Voltage [V]",
                "fname": f"Last",
                "values": cycle2_discharge,
            }
        )
        experiment_result.append({"graphs": graphs})

        final_result.append(experiment_result)

        experiment_result = [{"title": "Unmodified graphs"}]

        graphs = []

        print(len(cycle1_dsc_cap))
        print(len(cycle1_discharge))
        print(len(cycle2_dsc_cap))
        print(len(cycle2_discharge))

        graphs.append(
            {
                "name": "Throughput capacity [A.h]",
                "values": sol.cycles[0]["Throughput capacity [A.h]"].entries.tolist(),
            }
        )
        graphs.append(
            {
                "name": "Voltage [V]",
                "fname": f"First",
                "values": sol.cycles[0]["Voltage [V]"].entries.tolist(),
            }
        )

        graphs.append(
            {
                "name": "Throughput capacity [A.h]",
                "values": sol.cycles[1]["Throughput capacity [A.h]"].entries.tolist(),
            }
        )
        graphs.append(
            {
                "name": "Voltage [V]",
                "fname": f"Second",
                "values": sol.cycles[1]["Voltage [V]"].entries.tolist(),
            }
        )

        graphs.append(
            {
                "name": "Throughput capacity [A.h]",
                "values": sol.cycles[len(sol.cycles) - 1][
                    "Throughput capacity [A.h]"
                ].entries.tolist(),
            }
        )
        graphs.append(
            {
                "name": "Voltage [V]",
                "fname": f"Last",
                "values": sol.cycles[len(sol.cycles) - 1][
                    "Voltage [V]"
                ].entries.tolist(),
            }
        )
        experiment_result.append({"graphs": graphs})

        final_result.append(experiment_result)

        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
