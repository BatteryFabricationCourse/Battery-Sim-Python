from flask import jsonify
import pybamm
import numpy as np
from utils import update_parameters


def simulate_lab2(request):
    try:
        print("New Request: ", request.json)
        data = request.json
        temperature = data.get("Ambient temperature [K]")
        c_rates = data.get("C Rates", [1])
        silicon_percent = data.get("Silicon Percentage")

        model = pybamm.lithium_ion.DFN(
            {
                "particle phases": ("2", "1"),
                "open-circuit potential": (("single", "current sigmoid"), "single"),
            }
        )

        parameters = pybamm.ParameterValues("Chen2020_composite")

        parameters.update(
            {
                "Primary: Maximum concentration in negative electrode [mol.m-3]": 28700,
                "Primary: Initial concentration in negative electrode [mol.m-3]": 23000,
                "Primary: Negative electrode diffusivity [m2.s-1]": 5.5e-14,
                "Secondary: Negative electrode diffusivity [m2.s-1]": 1.67e-14,
                "Secondary: Initial concentration in negative electrode [mol.m-3]": 277000,
                "Secondary: Maximum concentration in negative electrode [mol.m-3]": 278000,
            }
        )
        update_parameters(parameters, temperature, None, None, silicon_percent)

        capacity = parameters["Nominal cell capacity [A.h]"]
        I_load = c_rates[0] * capacity

        parameters["Current function [A]"] = I_load

        fast_solver = pybamm.CasadiSolver("safe", dt_max=500)

        sim = pybamm.Simulation(model, parameter_values=parameters, solver=fast_solver)
        t_eval = np.linspace(0, 10000, 1000)
        sol = sim.solve(t_eval=t_eval)

        experiment_result1 = [{"title": f"Interfacial current density in silicon"}]
        graph1 = []
        graph1.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        graph1.append(
            {
                "name": "'Loss of capacity to SEI [A.h]",
                "fname": f"V",
                "values": sol[
                    "Loss of capacity to positive SEI [A.h]"
                ].entries.tolist(),
            }
        )
        experiment_result1.append({"graphs": graph1})

        experiment_result2 = [{"title": f"Graphite"}]
        graph2 = []
        graph2.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        graph2.append(
            {
                "name": "Averaged interfacial current density [A.m-2]",
                "fname": f"V",
                "values": sol[
                    "X-averaged negative electrode primary interfacial current density [A.m-2]"
                ].entries.tolist(),
            }
        )
        experiment_result2.append({"graphs": graph2})

        experiment_result3 = [{"title": f"Silicon"}]
        graph3 = []
        graph3.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        graph3.append(
            {
                "name": "Averaged interfacial current density [A.m-2]",
                "fname": f"V",
                "values": sol[
                    "X-averaged negative electrode secondary interfacial current density [A.m-2]"
                ].entries.tolist(),
            }
        )
        experiment_result3.append({"graphs": graph3})
        
        experiment_result4 = [{"title": f"Silicon"}]
        graph4 = []
        graph4.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        graph4.append(
            {
                "name": "Total lithium [mol]",
                "fname": f"Total",
                "values": sol[
                    "Total lithium [mol]"
                ].entries.tolist(),
            }
        )
        graph4.append(
            {
                "name": "Total lithium [mol]",
                "fname": f"Neg Electrode",
                "values": sol[
                    "Total lithium in negative electrode [mol]"
                ].entries.tolist(),
            }
        )
        experiment_result4.append({"graphs": graph4})

        final_result = [experiment_result1, experiment_result2, experiment_result3, experiment_result4]
        print("Request Answered: ", final_result)
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
