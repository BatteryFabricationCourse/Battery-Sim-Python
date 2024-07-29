from flask import jsonify
import pybamm
import utils
import numpy


# DONE Add c rates to Cycling
def simulate_lab1(request):
    try:
        print("New Request: ", request.json)
        data = request.json
        battery_type = data.get("Type")
        temperature = float(data.get("Ambient temperature [K]"))
        capacity = float(data.get("Nominal cell capacity [A.h]"))
        c_rates = data.get("C Rates", [1])
        cycles = int(data.get("Cycles", 1))

        if cycles > 50:
            cycles = 50

        if battery_type not in utils.batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = utils.get_battery_parameters(
            battery_type, degradation_enabled=False
        )
        utils.update_parameters(parameters, temperature, capacity, None, None)

        parameters.set_initial_stoichiometries(1)
        final_result = []
        final_result.append(
            utils.run_charging_experiments(battery_type, c_rates, "Charge", parameters)
        )
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
        utils.update_parameters(parameters, temperature, capacity, None, None)
        i = 0
        for c_rate in c_rates:
            i = i + 1
            c_experiment = pybamm.Experiment(
                [
                    (
                        f"Discharge at {c_rate + 0.001} C until {minV} V",
                        f"Charge at {c_rate + 0.001} C until {maxV} V",
                        f"Hold at {maxV}V until C/100",
                    )
                ]
                * (cycles - 1)
                + [f"Discharge at 0.1C until {minV} V (5 minute period)"]
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
                    "values": sol.summary_variables["Cycle number"].tolist(),
                }
            )
            print("i: ", i, " calc: ", len(c_rates)-i, " Actual C-Rate: ", c_rate, ", display c-rate: ", c_rates[len(c_rates)-i])
            graphs.append(
                {
                    "name": "Capacity [A.h]",
                    "fname": f"{c_rates[len(c_rates)-i]}C",
                    "values": sol.summary_variables["Capacity [A.h]"].tolist(),
                }
            )
            del sol

        experiment_result.append({"graphs": graphs})

        final_result.append(experiment_result)
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
