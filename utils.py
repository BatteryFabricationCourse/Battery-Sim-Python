import pybamm
import numpy as np
from scipy.interpolate import PchipInterpolator


def interpolate_array(input_array, output_size):
    """
    Interpolates the values in the input array to generate an output array of the specified size.

    Parameters:
    input_array (list or numpy array): The array of numbers to interpolate.
    output_size (int): The size of the output array.

    Returns:
    numpy array: The interpolated array of the specified size.
    """
    input_array = np.array(input_array)
    input_size = len(input_array)
    
    # Create the indices for the input and output arrays
    input_indices = np.arange(input_size)
    output_indices = np.linspace(0, input_size - 1, output_size)
    
    # Create the PCHIP interpolation function
    pchip_interp_func = PchipInterpolator(input_indices, input_array)
    
    # Interpolate the values
    output_array = pchip_interp_func(output_indices)
    
    return output_array.tolist()


def update_parameters(
    parameters, temperature, capacity, PosElectrodeThickness, silicon_percent
):
    if temperature and temperature != 0:
        parameters.update({"Ambient temperature [K]": float(temperature)})
    if capacity and capacity != 0:
        parameters.update({"Nominal cell capacity [A.h]": capacity})
    if PosElectrodeThickness and PosElectrodeThickness != 0:
        parameters.update({"Positive electrode thickness [m]": PosElectrodeThickness})
    if silicon_percent:
        silicon_percent *= 0.5
        parameters.update(
            {
                "Primary: Negative electrode active material volume fraction": (
                    1 - (silicon_percent)
                ),
                "Secondary: Negative electrode active material volume fraction": (
                    silicon_percent
                ),
            }
        )


def run_charging_experiments(c_rates, mode, model, parameters, solver):
    experiment_result = [{"title": f"{mode.capitalize()[:-1]}ing at different C Rates"}]
    graphs = []
    model = pybamm.lithium_ion.SPM()
    solver = pybamm.CasadiSolver()
    y_axis_label = None
    for c_rate in c_rates:
        #c_rate = c_rate + 0.01
        if mode == "Charge":
            experiment = pybamm.Experiment(
                [f"Charge at {c_rate}C for 3 hours or until 4.3 V"]
            )
            initial_soc = 0
            y_axis_label = "Throughput capacity [A.h]"
        else:
            experiment = pybamm.Experiment(
                [f"Discharge at {c_rate}C for 3 hours or until 2.0 V"]
            )
            initial_soc = 1
            y_axis_label = "Discharge capacity [A.h]"
        
        print(f"Running simulation C Rate: {c_rate} {mode.lower()[:-1]}ing\n")

        sim = pybamm.Simulation(
            model, parameter_values=parameters, experiment=experiment
        )
        sol = sim.solve(initial_soc=initial_soc, solver=solver)
        graphs.append(
            {"name": y_axis_label, "values": sol[y_axis_label].entries.tolist()}
        )
        graphs.append(
            {
                "name": "Voltage [V]",
                "fname": f"{c_rate}C",
                "values": sol["Voltage [V]"].entries.tolist(),
            }
        )

    experiment_result.append({"graphs": graphs})
    return experiment_result


def run_cycling_experiment(cycles, model, parameters):
    experiment_result = [{"title": "Cycling"}]
    graphs = []
    experiment = pybamm.Experiment(
        [
            (
                "Charge at 1 C until 4.0 V",
                "Hold at 4.0 V until C/10",
                "Rest for 5 minutes",
                "Discharge at 1 C until 2.2 V",
                "Rest for 5 minutes",
            )
        ]
        * cycles
    )
    sim = pybamm.Simulation(model, parameter_values=parameters, experiment=experiment)
    print("Running simulation Cycling\n")
    solver = pybamm.CasadiSolver("fast", dt_max=100000)
    sol = sim.solve(solver=solver)

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
    experiment_result2 = []
    experiment_result2.append({"title": "Temperature"})
    graphs = []
    graphs.append(
            {"name": "Time [s]", "values": sol["Time [s]"].entries.tolist()}
        )
    graphs.append(
            {
                "name": "Cell Temperature [C]",
                "fname": f"C",
                "values": sol["Cell temperature [C]"].entries.tolist(),
            }
        )
    
    experiment_result2.append({"graphs": graphs})
    return [experiment_result, experiment_result2]
