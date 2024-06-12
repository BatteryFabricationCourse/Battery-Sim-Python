import pybamm

# Define a function to simulate a battery with given parameters and degradation models
def simulate_battery(battery_name, parameter_set):
    # Create the model
    try:
        model = pybamm.lithium_ion.SPM({
        "particle mechanics": "swelling and cracking",
        })

        # Load parameter values for the battery
        param = pybamm.ParameterValues(parameter_set)

        # Add degradation models for particle cracking
        model.submodels["negative particle mechanics"] = pybamm.particle_mechanics.CrackPropagation(
            model.param, "Negative", True, model.options
        )
        model.submodels["positive particle mechanics"] = pybamm.particle_mechanics.CrackPropagation(
            model.param, "Positive", True, model.options
        )

        # Create a simulation
        sim = pybamm.Simulation(model, parameter_values=param)

        # Set up the simulation (e.g., initial conditions, timespan)
        t_eval = pybamm.linspace(0, 3600)  # Simulate for 1 hour
        sim.solve([0, 3600])

        # Plot the results
        sim.plot()
    except:
        print("Simulation Failed")

# Define the batteries and their parameter sets
batteries = {
    "NMC532": "OKane2022",
    "NCA": "NCA_Kim2011",
    "LFP": "Prada2013",
    "LG M50": "OKane2022"
}

# Simulate each battery
for battery_name, parameter_set in batteries.items():
    print(f"Simulating {battery_name} with parameter set {parameter_set}")
    simulate_battery(battery_name, parameter_set)
