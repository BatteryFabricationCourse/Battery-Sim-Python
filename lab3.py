from flask import jsonify
import pybamm
import numpy as np
from scipy.ndimage import interpolation
import utils


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
                    f"Charge at {(charge_current)} C for 10 hours or until {charge_voltage} V",
                    f"Hold at {hold_voltage} V for 2 hours or until C*{hold_current}",
                    f"Rest for {rest1_minutes} minutes",
                    f"Discharge at {(discharge_current)} C for 10 hours or until {discharge_voltage} V",
                    f"Rest for {rest2_minutes} minutes",
                )
            ]
            * cycles
        )

        sim = pybamm.Simulation(
            model, parameter_values=parameters, experiment=experiment
        )
        print("Running simulation Cycling\n")
        solver = pybamm.CasadiSolver(
            "safe", dt_max=0.01, extra_options_setup={"max_num_steps": 500}
        )
        sol = sim.solve(solver=solver, save_at_cycles=1, initial_soc=initial_charge)

        # Prepare data for plotting
        experiment_result = [{"title": "Capacity over Cycles"}]
        cap = []
        if battery_type == "NCA":
            cap = sol.summary_variables["Capacity [A.h]"].tolist()
        elif battery_type == "LFP":
            cap = utils.transform_to_inverse_bezier_curve(sol.summary_variables["Capacity [A.h]"], (cycles / 250.0) * ((charge_current + discharge_current) / 2))
        else:
            cap = utils.transform_to_inverse_bezier_curve(sol.summary_variables["Capacity [A.h]"], (cycles / 350.0) * ((charge_current + discharge_current) / 2))
        graphs.append(
            {
                "name": "Cycle",
                "round": True,
                "values": sol.summary_variables["Cycle number"].tolist(),
            }
        )
        graphs.append(
            {
                "name": "Capacity [A.h]",
                "fname": "Capacity",
                "values": cap,
            }
        )
        experiment_result.append({"graphs": graphs})
        final_result.append(experiment_result)

        experiment_result = [{"title": "Voltage over Cycles"}]

        experiment_result.append(
            {
                "graphs": utils.plot_against_cycle(
                    sol, cycles, "Voltage [V]", "Voltage", True
                )
            }
        )
        final_result.append(experiment_result)

        experiment_result = [{"title": "Charging in different Cycles"}]
        graphs = []

        # First cycle (cycle 0)
        charge_step1 = sol.cycles[0].steps[0]  # Charging step
        voltage_charge1 = charge_step1["Voltage [V]"].entries.tolist()
        throughput_cap_charge1 = charge_step1["Throughput capacity [A.h]"].entries.tolist()
        cycle1_crg_cap = [x - throughput_cap_charge1[0] for x in throughput_cap_charge1]  # Normalize to start at 0

        # Second cycle (cycle 1)
        charge_step2 = sol.cycles[1].steps[0]
        voltage_charge2 = charge_step2["Voltage [V]"].entries.tolist()
        throughput_cap_charge2 = charge_step2["Throughput capacity [A.h]"].entries.tolist()
        cycle2_crg_cap = [x - throughput_cap_charge2[0] for x in throughput_cap_charge2]

        # Last cycle
        charge_stepL = sol.cycles[-1].steps[0]
        voltage_chargeL = charge_stepL["Voltage [V]"].entries.tolist()
        throughput_cap_chargeL = charge_stepL["Throughput capacity [A.h]"].entries.tolist()
        cycleL_crg_cap = [x - throughput_cap_chargeL[0] for x in throughput_cap_chargeL]

        # Populate graphs
        graphs.append({"name": "Throughput capacity [A.h]", "values": cycle1_crg_cap})
        graphs.append({"name": "Voltage [V]", "fname": "First", "values": voltage_charge1})

        graphs.append({"name": "Throughput capacity [A.h]", "values": cycle2_crg_cap})
        graphs.append({"name": "Voltage [V]", "fname": "Second", "values": voltage_charge2})

        graphs.append({"name": "Throughput capacity [A.h]", "values": cycleL_crg_cap})
        graphs.append({"name": "Voltage [V]", "fname": "Last", "values": voltage_chargeL})

        experiment_result.append({"graphs": graphs})
        final_result.append(experiment_result)

        experiment_result = [{"title": "Discharging in different Cycles"}]

        graphs = []

# First cycle (cycle 0)
        discharge_step1 = sol.cycles[0].steps[3]  # Discharge step
        voltage_discharge1 = discharge_step1["Voltage [V]"].entries.tolist()
        throughput_cap_discharge1 = discharge_step1["Throughput capacity [A.h]"].entries.tolist()
        cycle1_dsc_cap = [x - throughput_cap_discharge1[0] for x in throughput_cap_discharge1]  # Normalize to start at 0

        # Second cycle (cycle 1)
        discharge_step2 = sol.cycles[1].steps[3]
        voltage_discharge2 = discharge_step2["Voltage [V]"].entries.tolist()
        throughput_cap_discharge2 = discharge_step2["Throughput capacity [A.h]"].entries.tolist()
        cycle2_dsc_cap = [x - throughput_cap_discharge2[0] for x in throughput_cap_discharge2]

        # Last cycle (cycle -1)
        discharge_stepL = sol.cycles[-1].steps[3]
        voltage_dischargeL = discharge_stepL["Voltage [V]"].entries.tolist()
        throughput_cap_dischargeL = discharge_stepL["Throughput capacity [A.h]"].entries.tolist()
        cycleL_dsc_cap = [x - throughput_cap_dischargeL[0] for x in throughput_cap_dischargeL]

        # Populate graphs for plotting
        graphs.append({"name": "Throughput capacity [A.h]", "values": cycle1_dsc_cap})
        graphs.append({"name": "Voltage [V]", "fname": "First", "values": voltage_discharge1})

        graphs.append({"name": "Throughput capacity [A.h]", "values": cycle2_dsc_cap})
        graphs.append({"name": "Voltage [V]", "fname": "Second", "values": voltage_discharge2})

        graphs.append({"name": "Throughput capacity [A.h]", "values": cycleL_dsc_cap})
        graphs.append({"name": "Voltage [V]", "fname": "Last", "values": voltage_dischargeL})

        experiment_result.append({"graphs": graphs})
        final_result.append(experiment_result)

        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
