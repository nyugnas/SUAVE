# mission_Electric_Helicopter.py
# 
# Created: Feb 2020, M Clarke

#----------------------------------------------------------------------
#   Imports
# ---------------------------------------------------------------------
import SUAVE
from SUAVE.Core import Units, Data 
import copy 
import sys
import pylab as plt
import numpy as np 
from copy import deepcopy  

sys.path.append('../Vehicles')
# the analysis functions

from Electric_Helicopter  import vehicle_setup, configs_setup 

# ----------------------------------------------------------------------
#   Setup
# ----------------------------------------------------------------------
def eh_full_setup():    
    
    # vehicle data
    vehicle  = vehicle_setup()
    configs  = eh_configs_setup(vehicle)
    
    # vehicle analyses
    configs_analyses = eh_analyses_setup(configs)

    # mission analyses
    mission  = eh_mission_setup(configs_analyses,vehicle)
    missions_analyses = eh_missions_setup(mission)

    analyses = SUAVE.Analyses.Analysis.Container()
    analyses.configs  = configs_analyses
    analyses.missions = missions_analyses
    
    return configs, analyses

# ----------------------------------------------------------------------
#   Define the Vehicle Analyses
# ----------------------------------------------------------------------

def eh_analyses_setup(configs):
    analyses = SUAVE.Analyses.Analysis.Container()

    # build a base analysis for each config
    for tag,config in configs.items():
        analysis = eh_base_analysis(config)
        analyses[tag] = analysis 
        
    return analyses


# ----------------------------------------------------------------------
#   Define the Configurations
# ---------------------------------------------------------------------

def eh_configs_setup(vehicle):
    # ------------------------------------------------------------------
    #   Initialize Configurations
    # ------------------------------------------------------------------

    configs = SUAVE.Components.Configs.Config.Container()

    base_config = SUAVE.Components.Configs.Config(vehicle)
    base_config.tag = 'base'
    configs.append(base_config)
    
    # ------------------------------------------------------------------
    #   Hover Configuration
    # ------------------------------------------------------------------
    config = SUAVE.Components.Configs.Config(base_config)
    config.tag = 'hover'
    config.propulsors.propulsor.pitch_command = 0.  * Units.degrees    
    configs.append(config)
    
    # ------------------------------------------------------------------
    #    Configuration
    # ------------------------------------------------------------------
    config = SUAVE.Components.Configs.Config(base_config)
    config.tag = 'climb'
    #config.propulsors.propulsor.thrust_angle  = 85 * Units.degrees    
    config.propulsors.propulsor.pitch_command = 0.  * Units.degrees    
    configs.append(config)
    
    return configs

def eh_base_analysis(vehicle):

    # ------------------------------------------------------------------
    #   Initialize the Analyses
    # ------------------------------------------------------------------     
    analyses = SUAVE.Analyses.Vehicle()

    # ------------------------------------------------------------------
    #  Basic Geometry Relations
    sizing = SUAVE.Analyses.Sizing.Sizing()
    sizing.features.vehicle = vehicle
    analyses.append(sizing)

    # ------------------------------------------------------------------
    #  Weights
    weights = SUAVE.Analyses.Weights.Weights_Electric_Helicopter()
    weights.vehicle = vehicle
    analyses.append(weights)

    # ------------------------------------------------------------------
    #  Aerodynamics Analysis
    aerodynamics = SUAVE.Analyses.Aerodynamics.Fidelity_Zero()
    aerodynamics.geometry = vehicle
    aerodynamics.settings.drag_coefficient_increment = 0.001
    analyses.append(aerodynamics)

    # ------------------------------------------------------------------
    #  Energy
    energy= SUAVE.Analyses.Energy.Energy()
    energy.network = vehicle.propulsors 
    analyses.append(energy)

    # ------------------------------------------------------------------
    #  Planet Analysis
    planet = SUAVE.Analyses.Planets.Planet()
    analyses.append(planet)

    # ------------------------------------------------------------------
    #  Atmosphere Analysis
    atmosphere = SUAVE.Analyses.Atmospheric.US_Standard_1976()
    atmosphere.features.planet = planet.features
    analyses.append(atmosphere)   

    return analyses    


def eh_mission_setup(analyses,vehicle):
    
      
    # ------------------------------------------------------------------
    #   Initialize the Mission
    # ------------------------------------------------------------------

    mission = SUAVE.Analyses.Mission.Sequential_Segments()
    mission.tag = 'mission'

    # airport
    airport            = SUAVE.Attributes.Airports.Airport()
    airport.altitude   =  0.0  * Units.ft
    airport.delta_isa  =  0.0
    airport.atmosphere = SUAVE.Attributes.Atmospheres.Earth.US_Standard_1976()

    mission.airport = airport    

    # unpack Segments module
    Segments = SUAVE.Analyses.Mission.Segments

    # base segment
    base_segment                                             = Segments.Segment()
    ones_row                                                 = base_segment.state.ones_row
    base_segment.process.iterate.initials.initialize_battery = SUAVE.Methods.Missions.Segments.Common.Energy.initialize_battery 
    base_segment.process.iterate.unknowns.network            = vehicle.propulsors.propulsor.unpack_unknowns
    base_segment.process.iterate.residuals.network           = vehicle.propulsors.propulsor.residuals
    base_segment.state.unknowns.propeller_power_coefficient  = 0.05 * ones_row(1) 
    base_segment.state.unknowns.battery_voltage_under_load   = 400. * ones_row(1)  # vehicle.propulsors.propulsor.battery.max_voltage * ones_row(1)     
    base_segment.state.unknowns.thurst_angle                 = 90. * Units.degrees * ones_row(1)
    base_segment.state.residuals.network                     = 0. * ones_row(3)    
    
    # VSTALL Calculation
    m      = vehicle.mass_properties.max_takeoff
    g      = 9.81
    S      = vehicle.reference_area
    atmo   = SUAVE.Analyses.Atmospheric.US_Standard_1976()
    rho    = atmo.compute_values(1000.*Units.feet,0.).density
    CLmax  = 1.2 
    Vstall = float(np.sqrt(2.*m*g/(rho*S*CLmax)))

    # ------------------------------------------------------------------
    #   First Climb Segment: Constant Speed, Constant Rate
    # ------------------------------------------------------------------

    segment     = Segments.Hover.Climb(base_segment)
    segment.tag = "Climb"

    segment.analyses.extend( analyses.climb) 
    segment.altitude_start  = 0.0  * Units.ft
    segment.altitude_end    = 40.  * Units.ft
    segment.climb_rate      = 300. * Units['ft/min']
    segment.battery_energy  = vehicle.propulsors.propulsor.battery.max_energy*0.95
    
    segment.state.unknowns.throttle                       = 0.5  * ones_row(1)
    segment.state.unknowns.propeller_power_coefficient    = 0.05 * ones_row(1) 

    segment.process.iterate.unknowns.network          = vehicle.propulsors.propulsor.unpack_unknowns
    segment.process.iterate.residuals.network         = vehicle.propulsors.propulsor.residuals
    segment.process.iterate.unknowns.mission          = SUAVE.Methods.skip
    segment.process.iterate.conditions.stability      = SUAVE.Methods.skip
    segment.process.finalize.post_process.stability   = SUAVE.Methods.skip 
    
    # add to misison
    mission.append_segment(segment)

    # ------------------------------------------------------------------
    #   Hover Segment: Constant Speed, Constant Rate
    # ------------------------------------------------------------------

    segment    = Segments.Hover.Hover(base_segment)
    segment.tag = "Hover" 
    segment.analyses.extend( analyses.hover )
 
    segment.altitude    = 40.  * Units.ft
    segment.time        = 2*60
    segment.state.unknowns.propeller_power_coefficient      = 0.04 * ones_row(1)     
    segment.state.unknowns.throttle                         = 0.7 * ones_row(1)
    
    segment.process.iterate.unknowns.network          = vehicle.propulsors.propulsor.unpack_unknowns 
    segment.process.iterate.residuals.network         = vehicle.propulsors.propulsor.residuals   
    segment.process.iterate.unknowns.mission          = SUAVE.Methods.skip
    segment.process.iterate.conditions.stability      = SUAVE.Methods.skip
    segment.process.finalize.post_process.stability   = SUAVE.Methods.skip 
    
    # add to misison
    mission.append_segment(segment)  

    return mission
         

def eh_missions_setup(base_mission):

    # the mission container
    missions = SUAVE.Analyses.Mission.Mission.Container()

    # ------------------------------------------------------------------
    #   Base Mission
    # ------------------------------------------------------------------

    missions.base = base_mission


    # done!
    return missions  


# ----------------------------------------------------------------------
#   Plot Results
# ----------------------------------------------------------------------
def eh_plot_mission(results): 
    
    axis_font = {'size':'14'} 
    line_color = 'bo-'
    fig = plt.figure( )
    fig.set_size_inches(12, 10)
    for i in range(len(results.segments)):  
    
        time           = results.segments[i].conditions.frames.inertial.time[:,0] / Units.min
        power          = results.segments[i].conditions.propulsion.battery_draw[:,0] 
        eta            = results.segments[i].conditions.propulsion.throttle[:,0]
        energy         = results.segments[i].conditions.propulsion.battery_energy[:,0] 
        volts          = results.segments[i].conditions.propulsion.voltage_under_load[:,0] 
        volts_oc       = results.segments[i].conditions.propulsion.voltage_open_circuit[:,0]     
        current        = results.segments[i].conditions.propulsion.current[:,0]      
        battery_amp_hr = (energy*0.000277778)/volts
        C_rating       = current/battery_amp_hr 
        
        axes = fig.add_subplot(2,2,1)
        axes.plot(time, eta, 'bo-' ) 
        axes.set_ylabel('Throttle')
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey') 
        axes.grid(True)       
        plt.ylim((0,1)) 
            
    
        axes = fig.add_subplot(2,2,2)
        axes.plot(time, energy*0.000277778, line_color)
        axes.set_ylabel('Battery Energy (W-hr)',axis_font)
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey')       
        axes.grid(True)   
    
        axes = fig.add_subplot(2,2,3)
        axes.plot(time, volts, 'bo-',label='Under Load')
        axes.plot(time,volts_oc, 'ks--',label='Open Circuit')
        axes.set_xlabel('Time (mins)',axis_font)
        axes.set_ylabel('Battery Voltage (Volts)',axis_font)  
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey')   
        if i == 0:
            axes.legend(loc='upper right')          
        axes.grid(True)         
        
        axes = fig.add_subplot(2,2,4)
        axes.plot(time, C_rating, line_color)
        axes.set_xlabel('Time (mins)',axis_font)
        axes.set_ylabel('C-Rating (C)',axis_font)  
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey')      
        axes.grid(True) 
        
        
    fig = plt.figure( )
    fig.set_size_inches(12, 10)  
    for segment in results.segments.values(): 

        time   = segment.conditions.frames.inertial.time[:,0] / Units.min
        rpm    = segment.conditions.propulsion.rpm[:,0] 
        thrust = segment.conditions.frames.body.thrust_force_vector[:,2]
        torque = segment.conditions.propulsion.motor_torque[:,0] 
        tm     = segment.conditions.propulsion.propeller_tip_mach[:,0]
 
        axes = fig.add_subplot(2,2,1)
        axes.plot(time, -thrust, line_color)
        axes.set_ylabel('Thrust (N)',axis_font)
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey')       
        axes.grid(True)   
        
        axes = fig.add_subplot(2,2,2)
        axes.plot(time, rpm, line_color)
        axes.set_ylabel('RPM',axis_font)
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey') 
        axes.grid(True)      
        
        axes = fig.add_subplot(2,2,3)
        axes.plot(time, torque, line_color )
        axes.set_xlabel('Time (mins)',axis_font)
        axes.set_ylabel('Torque (N-m)',axis_font)
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey')      
        axes.grid(True)   
        
        axes = fig.add_subplot(2,2,4)
        axes.plot(time, tm, line_color )
        axes.set_xlabel('Time (mins)',axis_font)
        axes.set_ylabel('Tip Mach',axis_font)
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey')      
        axes.grid(True) 
 
    fig = plt.figure( )
    fig.set_size_inches(12, 10)  
    for segment in results.segments.values(): 

        time   = segment.conditions.frames.inertial.time[:,0] / Units.min
        effp   = segment.conditions.propulsion.etap[:,0]
        effm   = segment.conditions.propulsion.etam[:,0]
        
        axes = fig.add_subplot(1,2,1)
        axes.plot(time, effp, line_color )
        axes.set_xlabel('Time (mins)',axis_font)
        axes.set_ylabel('Propeller Efficiency',axis_font)
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey')      
        axes.grid(True)           
        plt.ylim((0,1))
        
        axes = fig.add_subplot(1,2,2)
        axes.plot(time, effm, line_color )
        axes.set_xlabel('Time (mins)',axis_font)
        axes.set_ylabel('Motor Efficiency',axis_font)
        axes.minorticks_on()
        axes.grid(which='major', linestyle='-', linewidth='0.5', color='grey')
        axes.grid(which='minor', linestyle=':', linewidth='0.5', color='grey')      
        axes.grid(True)
         
    return
 