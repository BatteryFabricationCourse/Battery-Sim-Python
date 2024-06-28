from flask import jsonify
import pybamm
import numpy as np
import utils


def simulate_lab2(request):
    try:
        print("New Request: ", request.json)
        data = request.json
        temperature = data.get("Ambient temperature [K]")
        c_rates = data.get("C Rates", [1])
        cycles= 3
        silicon_percent = data.get("Silicon Percentage")

        model = pybamm.lithium_ion.DFN(
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
        utils.update_parameters(parameters, temperature, None, None, silicon_percent)


        fast_solver = pybamm.CasadiSolver("safe", dt_max=3600, extra_options_setup={"max_num_steps": 1000})
        s = pybamm.step.string
        cycling_experiment = pybamm.Experiment(
        [
            (
                s("Discharge at 1 C for 10 hours or until 3.0 V", period="1 hour"),
                s("Rest for 30 minutes", period="30 minutes"),
                s("Charge at 1 C until 4.1 V", period="30 minutes"),
                s("Hold at 4.1 V until 50 mA", period="30 minutes"),
                s("Rest for 30 minutes", period="30 minutes"),
            )
        ]
        * cycles,
    )

        print("Running experiment")
        sim = pybamm.Simulation(
            model,
            parameter_values=parameters,
            solver=fast_solver,
            experiment=cycling_experiment,
        )
        
        sol = sim.solve(calc_esoh=False, save_at_cycles=1)
        print("Number of Cycles: ", len(sol.cycles))
        print("Solution took: ", sol.solve_time)

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
        
        plots = {"Total lithium in positive electrode [mol]":"Positive", "Total lithium in negative electrode [mol]":"Negative", "Total lithium [mol]":"Total"}
        experiment_result1 = [{"title": "Total Lithium in electrodes"}, {"graphs": utils.plot_graphs_against_cycle(sol, 3, plots)}]
        
        
        
        
        experiment_result2 = [{"title": "Capacity over Cycles"}]
        experiment_result2.append({"graphs": utils.plot_against_cycle(sol, cycles, "Discharge capacity [A.h]", "Capacity")})
        final_result = [
            experiment_result1,
            experiment_result2,
        ]
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
