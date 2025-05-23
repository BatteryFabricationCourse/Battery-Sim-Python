from flask import jsonify
import pybamm
import numpy as np
import utils


def simulate_lab2(request):
    try:
        print("New Request: ", request.json)
        data: dict = request.json
        temperature: float = float(data.get("Ambient temperature [K]"))
        c_rate: float = data.get("C Rates", [1])[0]
        # cycles: int = 3
        silicon_percent: float = float(data.get("Silicon Percentage"))
        cycles = int(data.get("Cycles"))
        anode_thickness = float(data.get("Negative electrode thickness [um]"))
        seperator_thickness = float(data.get("Separator thickness [um]"))

        model = pybamm.lithium_ion.DFN(
            {
                "particle phases": ("2", "1"),
                "open-circuit potential": (("single", "current sigmoid"), "single"),
                "SEI": "solvent-diffusion limited",
                "SEI": "ec reaction limited",
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
        utils.update_parameters(
            parameters, temperature, None, None, silicon_percent, "LG M50"
        )

        fast_solver = pybamm.CasadiSolver(
            mode="safe", dt_max=0.01, extra_options_setup={"max_num_steps": 600}, return_solution_if_failed_early=True
        )
        s = pybamm.step.string
        # c_rate = utils.get_virtual_c_rate(c_rate)
        cycling_experiment = pybamm.Experiment(
            [
                (
                    
                    s(
                        f"Discharge at {c_rate} C for 11 hours or until 2.5 V",
                        period="1 minutes",
                    ),
                    s(f"Charge at {c_rate} C for 11 hours until 4.0 V", period="1 minutes"
                      ),
                    #s(f"Hold at 4.0 V for 1 hour or until 50 mA", period="0.5 minutes"),
                )
            ]
            * cycles,
        )

        print("Running experiment")
        if anode_thickness != None:
            parameters.update(
                {
                    "Negative electrode thickness [m]": anode_thickness * 1e-6,
                    "Separator thickness [m]": seperator_thickness * 1e-6,
                }
            )
        sim = pybamm.Simulation(
            model,
            parameter_values=parameters,
            solver=fast_solver,
            experiment=cycling_experiment,
        )
        sol = sim.solve(calc_esoh=False, save_at_cycles=1)
        print("Number of Cycles: ", len(sol.cycles))
        print("Solution took: ", sol.solve_time)

        plots = {
            "Total lithium in positive electrode [mol]": "Positive",
            "Total lithium in negative electrode [mol]": "Negative",
            "Total lithium [mol]": "Total",
        }
        experiment_result1 = [
            {"title": "Lithium in Electrodes"},
            {"graphs": utils.plot_graphs_against_cycle(sol, cycles, plots, "Lithium amount [mol]")},
        ]
        
        capacity_graph = []
        capacity_graph.append(
                {
                    "name": "Cycle",
                    "round": False,
                    # "values": utils.interpolate_array(sol.summary_variables["Cycle number"].tolist(), 24, True),
                    "values": sol.summary_variables["Cycle number"].tolist(),
                }
            )
        capacity_graph.append(
                {
                    "name": "Throughput capacity [A.h]",
                    # "fname": f"{c_rates[len(c_rates)-i]}C",
                    "fname": f"Capacity",
                    "values": sol.summary_variables["Throughput capacity [A.h]"].tolist(),
                    # "values": utils.interpolate_array(sol.summary_variables["Capacity [A.h]"].tolist(),24)
                }
            )
        experiment_result2 = [{"title": "Capacity over Cycles"},{"graphs": capacity_graph}]
        experiment_result3 = [
            {"title": "Interfacial Current Density"},
            {
                "graphs": utils.plot_graphs_against_cycle(
                    sol,
                    cycles,
                    {
                        "X-averaged negative electrode primary interfacial current density [A.m-2]": "Graphite",
                        "X-averaged negative electrode secondary interfacial current density [A.m-2]": "Silicon",
                    },
                    "interfacial current density [A.m-2]",
                )
            },
        ]

        experiment_result4 = [
            {"title": "Loss of Lithium"},
            {
                "graphs": utils.plot_graphs_against_cycle(
                    sol,
                    cycles,
                    {
                        "Loss of lithium inventory [%]": "Loss",
                    },
                )
            },
        ]

        final_result = [
            experiment_result2,
            experiment_result3,
            experiment_result1,
            experiment_result4,
        ]
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
