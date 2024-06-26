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

        model = pybamm.lithium_ion.SPMe(
            {
                "particle phases": ("2", "1"),
                "open-circuit potential": (("single", "current sigmoid"), "single"),
                "SEI": "solvent-diffusion limited"
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

        fast_solver = pybamm.CasadiSolver("fast with events", dt_max=10)
        #pybamm.settings.set_smoothing_parameters(1)

    #    cycling_experiment = pybamm.Experiment(
    #    [
    #        (
    #            "Charge at 1 C until 4.0 V",
    #            "Hold at 4.0 V until C/10",
    #            "Rest for 5 minutes",
    #            "Discharge at 1 C until 2.2 V",
    #            "Rest for 5 minutes",
    #        )
    #    ]
    #    * 20,
    #    #period="1 hour"
    #)

        print("Running experiment")
        sim = pybamm.Simulation(
            model,
            parameter_values=parameters,
            solver=fast_solver,
            #experiment=cycling_experiment,
        )
        t_eval = np.linspace(0, 36000, 1000)
        sol = sim.solve(calc_esoh=False, t_eval=t_eval)

        # Plot 1
        plot1 = []
        plot1.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        plot1.append(
            {
                "name": "Loss of active material in negative electrode [%]",
                "fname": "Negative",
                "values": sol[
                    "Loss of active material in negative electrode [%]"
                ].entries.tolist(),
            }
        )
        plot1.append(
            {
                "name": "Loss of active material in positive electrode [%]",
                "fname": "Positive",
                "values": sol[
                    "Loss of active material in positive electrode [%]"
                ].entries.tolist(),
            }
        )
        experiment_result1 = [{"title": "Loss of Active Material"}, {"graphs": plot1}]

        # Plot 2
        plot2 = []
        plot2.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        plot2.append(
            {
                "name": "Loss of capacity to positive SEI [A.h]",
                "fname": "Positive_SEI",
                "values": sol[
                    "Loss of capacity to positive SEI [A.h]"
                ].entries.tolist(),
            }
        )
        plot2.append(
            {
                "name": "Loss of capacity to positive SEI on cracks [A.h]",
                "fname": "Positive_SEI_Cracks",
                "values": sol[
                    "Loss of capacity to positive SEI on cracks [A.h]"
                ].entries.tolist(),
            }
        )
        plot2.append(
            {
                "name": "Loss of capacity to positive lithium plating [A.h]",
                "fname": "Positive_Lithium_Plating",
                "values": sol[
                    "Loss of capacity to positive lithium plating [A.h]"
                ].entries.tolist(),
            }
        )
        experiment_result2 = [{"title": "Loss of Capacity"}, {"graphs": plot2}]

        # Plot 3
        plot3 = []
        plot3.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        plot3.append(
            {
                "name": "Loss of lithium inventory [%]",
                "fname": "Lithium_Inventory",
                "values": sol["Loss of lithium inventory [%]"].entries.tolist(),
            }
        )
        plot3.append(
            {
                "name": "Loss of lithium inventory, including electrolyte [%]",
                "fname": "Lithium_Inventory_Electrolyte",
                "values": sol[
                    "Loss of lithium inventory, including electrolyte [%]"
                ].entries.tolist(),
            }
        )
        plot3.append(
            {
                "name": "Loss of lithium to positive SEI [mol]",
                "fname": "Lithium_Positive_SEI",
                "values": sol["Loss of lithium to positive SEI [mol]"].entries.tolist(),
            }
        )
        plot3.append(
            {
                "name": "Loss of lithium to positive SEI on cracks [mol]",
                "fname": "Lithium_Positive_SEI_Cracks",
                "values": sol[
                    "Loss of lithium to positive SEI on cracks [mol]"
                ].entries.tolist(),
            }
        )
        plot3.append(
            {
                "name": "Loss of lithium to positive lithium plating [mol]",
                "fname": "Lithium_Positive_Lithium_Plating",
                "values": sol[
                    "Loss of lithium to positive lithium plating [mol]"
                ].entries.tolist(),
            }
        )
        experiment_result3 = [{"title": "Loss of Lithium"}, {"graphs": plot3}]

        # Plot 4
        plot4 = []
        plot4.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        plot4.append(
            {
                "name": "Negative electrode capacity [A.h]",
                "fname": "Negative_Capacity",
                "values": sol["Negative electrode capacity [A.h]"].entries.tolist(),
            }
        )
        plot4.append(
            {
                "name": "Positive electrode capacity [A.h]",
                "fname": "Positive_Capacity",
                "values": sol["Positive electrode capacity [A.h]"].entries.tolist(),
            }
        )
        experiment_result4 = [
            {"title": "Change in Electrode Capacity"},
            {"graphs": plot4},
        ]

        # Plot 5
        plot5 = []
        plot5.append({"name": "Time [h]", "values": sol["Time [h]"].entries.tolist()})
        plot5.append(
            {
                "name": "Total lithium [mol]",
                "fname": "Total_Lithium",
                "values": sol["Total lithium [mol]"].entries.tolist(),
            }
        )
        plot5.append(
            {
                "name": "Total lithium in electrolyte [mol]",
                "fname": "Total_Lithium_Electrolyte",
                "values": sol["Total lithium in electrolyte [mol]"].entries.tolist(),
            }
        )
        plot5.append(
            {
                "name": "Total lithium in negative electrode [mol]",
                "fname": "Total_Lithium_Negative",
                "values": sol[
                    "Total lithium in negative electrode [mol]"
                ].entries.tolist(),
            }
        )
        plot5.append(
            {
                "name": "Total lithium in particles [mol]",
                "fname": "Total_Lithium_Particles",
                "values": sol["Total lithium in particles [mol]"].entries.tolist(),
            }
        )
        plot5.append(
            {
                "name": "Total lithium in positive electrode [mol]",
                "fname": "Total_Lithium_Positive",
                "values": sol[
                    "Total lithium in positive electrode [mol]"
                ].entries.tolist(),
            }
        )
        plot5.append(
            {
                "name": "Total lithium lost [mol]",
                "fname": "Total_Lithium_Lost",
                "values": sol["Total lithium lost [mol]"].entries.tolist(),
            }
        )
        plot5.append(
            {
                "name": "Total lithium lost from electrolyte [mol]",
                "fname": "Total_Lithium_Lost_Electrolyte",
                "values": sol[
                    "Total lithium lost from electrolyte [mol]"
                ].entries.tolist(),
            }
        )
        plot5.append(
            {
                "name": "Total lithium lost from particles [mol]",
                "fname": "Total_Lithium_Lost_Particles",
                "values": sol[
                    "Total lithium lost from particles [mol]"
                ].entries.tolist(),
            }
        )
        plot5.append(
            {
                "name": "Total lithium lost to side reactions [mol]",
                "fname": "Total_Lithium_Lost_Side_Reactions",
                "values": sol[
                    "Total lithium lost to side reactions [mol]"
                ].entries.tolist(),
            }
        )
        experiment_result5 = [{"title": "Total Lithium"}, {"graphs": plot5}]

        final_result = [
            experiment_result1,
            experiment_result2,
            experiment_result3,
            experiment_result4,
            experiment_result5,
        ]
        print("Request Answered: ", final_result)
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
