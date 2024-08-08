from flask import jsonify
import pybamm
import utils
import numpy


# DONE Add c rates to Cycling
def simulate_lab1(request):
    try:
        print("New Request: ", request.json)
        data = request.json
        battery_type: str = data.get("Type")
        temperature: float = float(data.get("Ambient temperature [K]"))
        capacity: float = float(data.get("Nominal cell capacity [A.h]"))
        c_rates: list = data.get("C Rates", [1])
        cycles: int = int(data.get("Cycles", 1))

        if cycles > 50:
            cycles = 50

        if battery_type not in utils.batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = utils.get_battery_parameters(
            battery_type, degradation_enabled=False
        )
        utils.update_parameters(
            parameters, temperature, capacity, None, None, battery_type
        )

        final_result = []
        final_result.append(
            utils.run_charging_experiments(battery_type, c_rates, "Charge", parameters)
        )

        parameters.set_initial_stoichiometries(1)
        final_result.append(
            utils.run_charging_experiments(
                battery_type, c_rates, "Discharge", parameters
            )
        )

        # Cycling
        experiment_result = [{"title": "Cycling"}]
        minV, maxV = utils.get_voltage_limits(battery_type)
        graphs = []
        parameters = utils.get_battery_parameters(
            battery_type, degradation_enabled=True
        )
        utils.update_parameters(
            parameters, temperature, capacity, None, None, battery_type
        )
        i = 0
        for c_rate in c_rates:
            i = i + 1
            v_crate = utils.get_virtual_c_rate(float(c_rate))
            print("V C-rate: ", v_crate, " for ", c_rate)

            c_experiment = pybamm.Experiment(
                [
                    (
                        f"Charge at {v_crate} C for 10 hours or until {maxV} V",
                        f"Discharge at {v_crate} C for 10 hours or until {minV} V",
                        f"Hold at {maxV}V for 1 hour or until C/100",
                    )
                ]
                * cycles
            )

            c_model = pybamm.lithium_ion.SPM({"SEI": "ec reaction limited"})
            sim = pybamm.Simulation(
                c_model, parameter_values=parameters, experiment=c_experiment
            )
            print("Running simulation Cycling\n")
            solver = pybamm.CasadiSolver("safe")
            sol = sim.solve(solver=solver)

            graphs.append(
                {
                    "name": "Cycle",
                    "round": True,
                    # "values": utils.interpolate_array(sol.summary_variables["Cycle number"].tolist(), 24, True),
                    "values": sol.summary_variables["Cycle number"].tolist(),
                }
            )
            graphs.append(
                {
                    "name": "Discharge capacity [A.h]",
                    # "fname": f"{c_rates[len(c_rates)-i]}C",
                    "fname": f"{c_rate}C",
                    "values": sol.summary_variables["Capacity [A.h]"].tolist(),
                    # "values": utils.interpolate_array(sol.summary_variables["Capacity [A.h]"].tolist(),24)
                }
            )
            del sol

        print("Cycling Graph: ", graphs)
        experiment_result.append({"graphs": graphs})

        final_result.append(experiment_result)
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
