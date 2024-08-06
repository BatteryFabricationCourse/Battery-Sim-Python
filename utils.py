import pybamm
import numpy as np
from scipy.interpolate import PchipInterpolator

# Battery titles in the front end mapping to the parameter set in PyBAMM
batteries: dict = {
    "NMC": "Mohtat2020",
    "NCA": "NCA_Kim2011",
    "LFP": "Prada2013",
    "LG M50": "OKane2022",
    "Silicon": "Chen2020_composite",
    "LFPBackup": "Ecker2015",
}


# Add voltage limit for lfp 3.65, 2.5, NMC 4.2, 3, NCA, 4.3, 2.5
def get_voltage_limits(battery_type: str) -> (int, int):
    if battery_type == "LFP":
        return 2.5, 3.65
    if battery_type == "NMC":
        return 3, 4.2
    if battery_type == "NCA":
        return 2.5, 4.3


# Interpolate array to given size
def interpolate_array(input_array: list, output_size: int) -> list:
    input_array = np.array(input_array)
    input_size = len(input_array)

    input_indices = np.arange(input_size)
    output_indices = np.linspace(0, input_size - 1, output_size)

    pchip_interp_func = PchipInterpolator(input_indices, input_array)

    output_array = pchip_interp_func(output_indices)

    return output_array.tolist()


# Cut the array in half, select every other element
def remove_every_other_from_array(list: list) -> list:
    return list[::2]


def get_battery_parameters(
    battery_type: str, degradation_enabled=False
) -> pybamm.ParameterValues:
    parameters = pybamm.ParameterValues(batteries[battery_type])

    # Lower the "SEI kinetic rate constant [m.s-1]" value to increase battery degradation rate. 1e-14 = 1x10^-14
    if degradation_enabled:
        if battery_type == "NCA":
            parameters.update(
                {"SEI kinetic rate constant [m.s-1]": 1e-14}, check_already_exists=False
            )
            pass
        elif battery_type == "NMC":
            # parameters.update(
            #    {"SEI kinetic rate constant [m.s-1]": 1e-14},
            #    check_already_exists=False,
            # )
            pass
        elif battery_type == "LFP":
            # parameters.update(
            #    {"SEI kinetic rate constant [m.s-1]": 1e-14},
            #    check_already_exists=False,
            # )
            parameters = pybamm.ParameterValues(batteries["NMC"])
            lfp_parameters = pybamm.ParameterValues(batteries["LFP"])
            parameters.update(lfp_parameters, check_already_exists=False)

    return parameters


# Returns graph dictionary ready to be sent to the front-end
def plot_against_cycle(
    solution: pybamm.Solution, number_of_cycles: int, variable_name: str, func_name=""
) -> list:
    function = []

    graphs = []
    for cycle in solution.cycles:
        function += cycle[variable_name].entries.tolist()

    print("Number of Samples: ", len(function))
    # while len(function) > 8100:
    #    function = remove_every_other_from_array(function)

    cycles_array = np.linspace(0, number_of_cycles, len(function))
    graphs.append(
        {
            "name": "Cycle",
            "values": cycles_array.tolist(),
        }
    )
    graphs.append(
        {
            "name": variable_name,
            "fname": func_name,
            "values": function,
        }
    )

    return graphs


def split_at_peak(arr: list) -> list:
    if len(arr) == 0:
        return np.array([]), np.array(
            []
        )  # Return empty arrays if the input array is empty

    peak_index = np.argmax(arr)  # Find the index of the peak value (maximum value)
    left_part = arr[:peak_index]  # Elements to the left of the peak
    right_part = arr[peak_index + 1 :]  # Elements to the right of the peak

    return left_part, right_part


def split_at_valley(arr) -> list:
    if len(arr) == 0:
        return np.array([]), np.array(
            []
        )  # Return empty arrays if the input array is empty

    valley_index = np.argmin(arr)  # Find the index of the valley value (minimum value)
    left_part = arr[:valley_index]  # Elements to the left of the valley
    right_part = arr[valley_index + 1 :]  # Elements to the right of the valley

    return left_part, right_part


def norm_array_start(arr) -> list:
    offset = arr[0]
    for i in range(0, len(arr)):
        print(i, ": ", arr[i], " - ", offset)
        arr[i] -= offset
    return arr


# Returns graphs dictionary ready to be sent to the front-end
def plot_graphs_against_cycle(
    solution: pybamm.Solution,
    number_of_cycles: int,
    variables: list,
    y_axis_name: str = None,
) -> list:
    graphs = []
    for variable_name in variables:
        function = []
        if y_axis_name == None:
            y_axis_name = variable_name
        for cycle in solution.cycles:
            function += cycle[variable_name].entries.tolist()
        cycles_array = np.linspace(0, number_of_cycles, len(function))
        graphs.append(
            {
                "name": "Cycle",
                "values": cycles_array.tolist(),
            }
        )
        graphs.append(
            {
                "name": y_axis_name,
                "fname": variables[variable_name],
                "values": function,
            }
        )

    return graphs


def extract_values_from_sub_sol(
    solution: pybamm.Solution, x_property: str, y_property: str, start: int, end: int
) -> (list, list):
    x_return = []
    y_return = []
    print("Extracting values...")
    for i in range(start, end):
        if i >= len(solution.sub_solutions):
            print("i too big, breaking", i, " end: ", end)
            break
        if i != start:
            x_return += (
                solution.sub_solutions[i][x_property].entries + x_return[-1]
            ).tolist()
            print("Added offset, ", i)
        else:
            x_return += solution.sub_solutions[i][x_property].entries.tolist()
            print("Added first element")

        y_return += solution.sub_solutions[i][y_property].entries.tolist()

    print("complete")
    return x_return, y_return


def update_parameters(
    parameters: pybamm.ParameterValues,
    temperature: float,
    capacity: float,
    PosElectrodeThickness: float,
    silicon_percent: float,
    battery_type: str,
) -> None:
    if temperature and temperature != 0:
        parameters.update({"Ambient temperature [K]": temperature})
    if capacity and capacity != 0:
        if battery_type == "NMC" and capacity == 5:
            return
        nominal_capacity = parameters.get(
            "Nominal cell capacity [A.h]"
        )  # Default to 1.0 if not set
        nominal_height = parameters.get(
            "Electrode height [m]"
        )  # Default to 1.0 if not set

        # Calculate the new height to achieve the desired capacity
        new_height = nominal_height * (capacity / nominal_capacity)
        if battery_type == "NCA":
            new_height = new_height * (10 / 11.77)
        if battery_type == "NMC" and capacity != 5:
            new_height = new_height * (10 / 9.67)

        # Update parameters with the new height
        parameters.update({"Electrode height [m]": new_height})
        parameters.update({"Nominal cell capacity [A.h]": capacity}, False)
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


def run_charging_experiments(
    battery_type: str, c_rates: list, mode: str, parameters: pybamm.ParameterValues
) -> dict:
    experiment_result = [{"title": f"{mode.capitalize()[:-1]}ing at different C Rates"}]
    graphs = []
    model = pybamm.lithium_ion.SPM()
    solver = pybamm.CasadiSolver("fast")
    y_axis_label = None
    minV, maxV = get_voltage_limits(battery_type)
    for c_rate in c_rates:

        if mode == "Charge":
            experiment = pybamm.Experiment(
                [f"Charge at {c_rate + 0.01}C for 100 hours or until {maxV} V"]
            )
            initial_soc = 0
            y_axis_label = "Throughput capacity [A.h]"
        else:
            experiment = pybamm.Experiment(
                [f"Discharge at {c_rate+ 0.01}C for 100 hours or until {minV} V"]
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
