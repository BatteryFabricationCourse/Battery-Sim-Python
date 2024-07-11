from flask import jsonify
import pybamm
import utils
import numpy

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

        if battery_type not in utils.batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = utils.get_battery_parameters(battery_type, degradation_enabled=False)
        utils.update_parameters(parameters, temperature, capacity, None, None)

        solver = pybamm.CasadiSolver("fast")
        model = pybamm.lithium_ion.SPM()
        
        parameters.set_initial_stoichiometries(1);
        final_result = []
        final_result.append(
            utils.run_charging_experiments(c_rates, "Charge", model, parameters, solver)
        )
        final_result.append(
            utils.run_charging_experiments(
                c_rates, "Discharge", model, parameters, solver
            )
        )
        
        
        
        #Cycling
        parameters = utils.get_battery_parameters(battery_type,  degradation_enabled=True)
        experiment = pybamm.Experiment(
            [
                (f"Discharge at 1C until 2V",
                f"Charge at 1C until 4V",
                f"Hold at 4.2V until C/50"
    )
            ]
            * cycles
        )
        
        model = pybamm.lithium_ion.SPM({"SEI": "ec reaction limited"})
        sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment)
        print("Running simulation Cycling\n")
        solver = pybamm.CasadiSolver("safe")
        sol = sim.solve(solver=solver)

        experiment_result = [{"title": "Cycling"}]
        graphs = []
        print(sol.summary_variables["Maximum measured discharge capacity [A.h]"].tolist())
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
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
