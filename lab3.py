from flask import jsonify
import pybamm
import numpy as np
from scipy.ndimage import interpolation
import utils

batteries = {
    "NMC": "Mohtat2020",
    "NCA": "NCA_Kim2011",
    "LFP": "Prada2013",
    "LG M50": "OKane2022",
    "Silicon": "Chen2020_composite",
    "LFPBackup": "Ecker2015",
}


def simulate_lab3(request):
    try:
        print("New Request: ", request.json)
        data = request.json
        battery_type = data.get("Type")
        temperature = data.get("Ambient temperature [K]")

        charging_properties = data.get("Charging Properties")
        charge_current = charging_properties.get("Charge C", 1)
        charge_voltage = charging_properties.get("Charge V", 1)
        hold_voltage = charging_properties.get("Hold V", 1)
        hold_current = charging_properties.get("Hold C", 1)
        rest1_minutes = charging_properties.get("Rest T", 1)
        discharge_current = charging_properties.get("Discharge C", 1)
        discharge_voltage = charging_properties.get("Discharge V", 1)
        rest2_minutes = charging_properties.get("Rest 2T", 1)
        cycles = charging_properties.get("Cycles", 1)

        if cycles > 50:
            cycles = 50

        if battery_type == "LFP":
            battery_type = "LFPBackup"
        if battery_type not in batteries:
            return jsonify({"error": "Unsupported chemistry"}), 400

        parameters = pybamm.ParameterValues(batteries[battery_type])
        utils.update_parameters(parameters, temperature, None, None, None)

        final_result = []
        graphs = []
        experiment = pybamm.Experiment(
            [
                (
                    f"Charge at {charge_current} C until {charge_voltage} V",
                    f"Hold at {hold_voltage} V until C*{hold_current}",
                    f"Rest for {rest1_minutes} minutes",
                    f"Discharge at {discharge_current} C until {discharge_voltage} V",
                    f"Rest for {rest2_minutes} minutes",
                )
            ]
            * cycles
        )
        model = None
        if battery_type == "LFP":
            #enable_LFP_degradation(parameters)
            model = pybamm.lithium_ion.SPM()
        else:
            model = pybamm.lithium_ion.SPM({"SEI": "ec reaction limited"})
            parameters.update({"SEI kinetic rate constant [m.s-1]": 1e-14}, check_already_exists=False)
            pass
        
        
        sim = pybamm.Simulation(
            model, parameter_values=parameters, experiment=experiment
        )
        print("Running simulation Cycling\n")
        solver = pybamm.CasadiSolver("fast", dt_max=10000)
        sol = sim.solve(solver=solver, save_at_cycles=1, initial_soc=0.1)

        
        # Prepare data for plotting
        experiment_result = [{"title": "Capacity over Cycles"}]
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

        experiment_result = [{"title": "Voltage over Cycles"}]
        
        experiment_result.append({"graphs": utils.plot_against_cycle(sol, cycles, "Voltage [V]", "Voltage")})
        final_result.append(experiment_result)

        return jsonify(final_result)

    except Exception as e:
        print(e)
        return jsonify(["ERROR: " + str(e)])





def enable_LFP_degradation(param):
    
    def graphite_LGM50_ocp_Chen2020(sto):
        """
        LG M50 Graphite open-circuit potential as a function of stochiometry, fit taken
        from [1]. Prada2013 doesn't give an OCP for graphite, so we use this instead.

        References
        ----------
        .. [1] Chang-Hui Chen, Ferran Brosa Planella, Kieran O’Regan, Dominika Gastol, W.
        Dhammika Widanage, and Emma Kendrick. "Development of Experimental Techniques for
        Parameterization of Multi-scale Lithium-ion Battery Models." Journal of the
        Electrochemical Society 167 (2020): 080534.

        Parameters
        ----------
        sto: :class:`pybamm.Symbol`
            Electrode stochiometry

        Returns
        -------
        :class:`pybamm.Symbol`
            Open-circuit potential
        """

        u_eq = (
            1.9793 * np.exp(-39.3631 * sto)
            + 0.2482
            - 0.0909 * np.tanh(29.8538 * (sto - 0.1234))
            - 0.04478 * np.tanh(14.9159 * (sto - 0.2769))
            - 0.0205 * np.tanh(30.4444 * (sto - 0.6103))
        )

        return u_eq


    def graphite_LGM50_electrolyte_exchange_current_density_Chen2020(
        c_e, c_s_surf, c_s_max, T
    ):
        """
        Exchange-current density for Butler-Volmer reactions between graphite and LiPF6 in
        EC:DMC.

        References
        ----------
        .. [1] Chang-Hui Chen, Ferran Brosa Planella, Kieran O’Regan, Dominika Gastol, W.
        Dhammika Widanage, and Emma Kendrick. "Development of Experimental Techniques for
        Parameterization of Multi-scale Lithium-ion Battery Models." Journal of the
        Electrochemical Society 167 (2020): 080534.

        Parameters
        ----------
        c_e : :class:`pybamm.Symbol`
            Electrolyte concentration [mol.m-3]
        c_s_surf : :class:`pybamm.Symbol`
            Particle concentration [mol.m-3]
        c_s_max : :class:`pybamm.Symbol`
            Maximum particle concentration [mol.m-3]
        T : :class:`pybamm.Symbol`
            Temperature [K]

        Returns
        -------
        :class:`pybamm.Symbol`
            Exchange-current density [A.m-2]
        """
        m_ref = 6.48e-7  # (A/m2)(m3/mol)**1.5 - includes ref concentrations
        E_r = 35000
        arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))

        return m_ref * arrhenius * c_e**0.5 * c_s_surf**0.5 * (c_s_max - c_s_surf) ** 0.5


    def LFP_ocp_Afshar2017(sto):
        """
        Open-circuit potential for LFP. Prada2013 doesn't give an OCP for LFP, so we use
        Afshar2017 instead.

        References
        ----------
        .. [1] Afshar, S., Morris, K., & Khajepour, A. (2017). Efficient electrochemical
        model for lithium-ion cells. arXiv preprint arXiv:1709.03970.

        Parameters
        ----------
        sto : :class:`pybamm.Symbol`
        Stochiometry of material (li-fraction)

        """

        c1 = -150 * sto
        c2 = -30 * (1 - sto)
        k = 3.4077 - 0.020269 * sto + 0.5 * np.exp(c1) - 0.9 * np.exp(c2)

        return k


    def LFP_electrolyte_exchange_current_density_kashkooli2017(c_e, c_s_surf, c_s_max, T):
        """
        Exchange-current density for Butler-Volmer reactions between LFP and electrolyte

        References
        ----------
        .. [1] Kashkooli, A. G., Amirfazli, A., Farhad, S., Lee, D. U., Felicelli, S., Park,
        H. W., ... & Chen, Z. (2017). Representative volume element model of lithium-ion
        battery electrodes based on X-ray nano-tomography. Journal of Applied
        Electrochemistry, 47(3), 281-293.

        Parameters
        ----------
        c_e : :class:`pybamm.Symbol`
            Electrolyte concentration [mol.m-3]
        c_s_surf : :class:`pybamm.Symbol`
            Particle concentration [mol.m-3]
        c_s_max : :class:`pybamm.Symbol`
            Maximum particle concentration [mol.m-3]
        T : :class:`pybamm.Symbol`
            Temperature [K]

        Returns
        -------
        :class:`pybamm.Symbol`
            Exchange-current density [A.m-2]
        """

        m_ref = 6 * 10 ** (-7)  # (A/m2)(m3/mol)**1.5 - includes ref concentrations
        E_r = 39570
        arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))

        return m_ref * arrhenius * c_e**0.5 * c_s_surf**0.5 * (c_s_max - c_s_surf) ** 0.5


    def electrolyte_conductivity_Prada2013(c_e, T):
        """
        Conductivity of LiPF6 in EC:EMC (3:7) as a function of ion concentration. The data
        comes from :footcite:`Prada2013`.

        Parameters
        ----------
        c_e: :class:`pybamm.Symbol`
            Dimensional electrolyte concentration
        T: :class:`pybamm.Symbol`
            Dimensional temperature

        Returns
        -------
        :class:`pybamm.Symbol`
            Solid conductivity
        """
        # convert c_e from mol/m3 to mol/L
        c_e = c_e / 1e6

        sigma_e = (
            4.1253e-4
            + 5.007 * c_e
            - 4721.2 * c_e**2
            + 1.5094e6 * c_e**3
            - 1.6018e8 * c_e**4
        ) * 1e3

        return sigma_e


    params = pybamm.ParameterValues("OKane2022")
    param.update({
        # cell
        "Negative electrode thickness [m]": 3.4e-05,
        "Separator thickness [m]": 2.5e-05,
        "Positive electrode thickness [m]": 8e-05,
        "Electrode height [m]": 0.6,  # to give an area of 0.18 m2
        "Electrode width [m]": 0.3,  # to give an area of 0.18 m2
        "Nominal cell capacity [A.h]": 2.3,
        "Current function [A]": 2.3,
        "Contact resistance [Ohm]": 0,
        # negative electrode
        "Negative electrode conductivity [S.m-1]": 215.0,
        "Maximum concentration in negative electrode [mol.m-3]": 30555,
        "Negative particle diffusivity [m2.s-1]": 3e-15,
        "Negative electrode OCP [V]": graphite_LGM50_ocp_Chen2020,
        "Negative electrode porosity": 0.36,
        "Negative electrode active material volume fraction": 0.58,
        "Negative particle radius [m]": 5e-6,
        "Negative electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Negative electrode Bruggeman coefficient (electrode)": 1.5,
        "Negative electrode charge transfer coefficient": 0.5,
        "Negative electrode double-layer capacity [F.m-2]": 0.2,
        "Negative electrode exchange-current density [A.m-2]"
        "": graphite_LGM50_electrolyte_exchange_current_density_Chen2020,
        "Negative electrode OCP entropic change [V.K-1]": 0,
        # positive electrode
        "Positive electrode conductivity [S.m-1]": 0.33795074,
        "Maximum concentration in positive electrode [mol.m-3]": 22806.0,
        "Positive particle diffusivity [m2.s-1]": 5.9e-18,
        "Positive electrode OCP [V]": LFP_ocp_Afshar2017,
        "Positive electrode porosity": 0.426,
        "Positive electrode active material volume fraction": 0.374,
        "Positive particle radius [m]": 5e-08,
        "Positive electrode Bruggeman coefficient (electrode)": 1.5,
        "Positive electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Positive electrode charge transfer coefficient": 0.5,
        "Positive electrode double-layer capacity [F.m-2]": 0.2,
        "Positive electrode exchange-current density [A.m-2]"
        "": LFP_electrolyte_exchange_current_density_kashkooli2017,
        "Positive electrode OCP entropic change [V.K-1]": 0,
        # separator
        "Separator porosity": 0.45,
        "Separator Bruggeman coefficient (electrolyte)": 1.5,
        # electrolyte
        "Initial concentration in electrolyte [mol.m-3]": 1200.0,
        "Cation transference number": 0.36,
        "Thermodynamic factor": 1.0,
        "Electrolyte diffusivity [m2.s-1]": 2e-10,
        "Electrolyte conductivity [S.m-1]": electrolyte_conductivity_Prada2013,
        # experiment
        "Reference temperature [K]": 298,
        "Ambient temperature [K]": 298,
        "Number of electrodes connected in parallel to make a cell": 1.0,
        "Number of cells connected in series to make a battery": 1.0,
        "Lower voltage cut-off [V]": 2.0,
        "Upper voltage cut-off [V]": 3.6,
        "Open-circuit voltage at 0% SOC [V]": 2.0,
        "Open-circuit voltage at 100% SOC [V]": 3.6,
        # initial concentrations adjusted to give 2.3 Ah cell with 3.6 V OCV at 100% SOC
        # and 2.0 V OCV at 0% SOC
        "Initial concentration in negative electrode [mol.m-3]": 0.81 * 30555,
        "Initial concentration in positive electrode [mol.m-3]": 0.0038 * 22806,
        "Initial temperature [K]": 298,
        }, check_already_exists=False)
    print("Enabled LFP degradation")
    