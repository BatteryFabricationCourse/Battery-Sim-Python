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
        cycles: int = 3
        silicon_percent: float = data.get("Silicon Percentage")

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
        utils.update_parameters(parameters, temperature, None, None, silicon_percent)

        fast_solver = pybamm.CasadiSolver(
            "safe", dt_max=3600, extra_options_setup={"max_num_steps": 1000}
        )
        s = pybamm.step.string
        cycling_experiment = pybamm.Experiment(
            [
                (
                    s(
                        f"Discharge at {c_rate} C for 10 hours or until 2.5 V",
                        period="1 hour",
                    ),
                    s(f"Charge at {c_rate} C until 4.3 V", period="30 minutes"),
                    # s(f"Hold at 4.1 V until 50 mA", period="30 minutes"),
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

        plots = {
            "Total lithium in positive electrode [mol]": "Positive",
            "Total lithium in negative electrode [mol]": "Negative",
            "Total lithium [mol]": "Total",
        }
        experiment_result1 = [
            {"title": "Total Lithium in electrodes"},
            {"graphs": utils.plot_graphs_against_cycle(sol, cycles, plots)},
        ]
        experiment_result2 = [{"title": "Capacity over Cycles"}]
        experiment_result2.append(
            {
                "graphs": utils.plot_against_cycle(
                    sol, cycles, "Discharge capacity [A.h]", "Capacity"
                )
            }
        )
        

        experiment_result3 = [
            {"title": "interfacial current density [A.m-2]"},
            {
                "graphs": utils.plot_graphs_against_cycle(
                    sol,
                    cycles,
                    {
                        "X-averaged negative electrode primary interfacial current density [A.m-2]": "Graphite",
                        "X-averaged negative electrode secondary interfacial current density [A.m-2]": "Silicon",
                    },
                    "interfacial current density [A.m-2]"
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
            experiment_result1,
            experiment_result2,
            experiment_result3,
            experiment_result4,
        ]
        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])
