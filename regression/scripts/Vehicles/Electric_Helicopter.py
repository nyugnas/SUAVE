# Electric_Helicopter.py
# 
# Created: Feb 2020, M Clarke

#----------------------------------------------------------------------
#   Imports
# ---------------------------------------------------------------------
import SUAVE
from SUAVE.Core import Units, Data
import copy
from SUAVE.Components.Energy.Networks.Vectored_Thrust import Vectored_Thrust
from SUAVE.Methods.Power.Battery.Sizing import initialize_from_mass
from SUAVE.Methods.Propulsion.electric_motor_sizing import size_from_mass
from SUAVE.Methods.Propulsion import propeller_design
from SUAVE.Methods.Aerodynamics.Fidelity_Zero.Lift import compute_max_lift_coeff 
from SUAVE.Methods.Weights.Buildups.Electric_Helicopter.empty import empty
from SUAVE.Methods.Utilities.Chebyshev  import chebyshev_data
from SUAVE.Methods.Propulsion.electric_motor_sizing import size_from_mass , compute_optimal_motor_parameters
from SUAVE.Methods.Weights.Correlations.Propulsion import nasa_motor, hts_motor , air_cooled_motor
import numpy as np

# ----------------------------------------------------------------------
#   Build the Vehicle
# ----------------------------------------------------------------------
def vehicle_setup():
    
    # ------------------------------------------------------------------
    #   Initialize the Vehicle
    # ------------------------------------------------------------------    
    vehicle               = SUAVE.Vehicle()
    vehicle.tag           = 'multicopter'
    vehicle.configuration = 'eVTOL'
    # ------------------------------------------------------------------
    #   Vehicle-level Properties
    # ------------------------------------------------------------------    
    # mass properties
    vehicle.mass_properties.takeoff           = 3000. * Units.lb 
    vehicle.mass_properties.operating_empty   = 2000. * Units.lb               # Approximate
    vehicle.mass_properties.max_takeoff       = 3000. * Units.lb               # Approximate
    vehicle.mass_properties.center_of_gravity = [8.5*0.3048 ,   0.  ,  0.*0.3048 ] # Approximate
    
     
    # This needs updating
    vehicle.passengers                        = 5
    vehicle.reference_area                    = 73  * Units.feet**2	
    vehicle.envelope.ultimate_load            = 5.7   
    vehicle.envelope.limit_load               = 3.  
   
    wing = SUAVE.Components.Wings.Main_Wing()
    wing.tag	                = 'main_wing'		
    wing.aspect_ratio	        = 1	 
    wing.spans.projected        = 0.01
    vehicle.append_component(wing)
    
    # ------------------------------------------------------				
    # FUSELAGE				
    # ------------------------------------------------------				
    # FUSELAGE PROPERTIES
    fuselage = SUAVE.Components.Fuselages.Fuselage()
    fuselage.tag                                = 'fuselage'
    fuselage.configuration	                = 'Tube_Wing'		
    fuselage.origin	                        = [[0. , 0.,  0.]]	
    fuselage.seats_abreast	                = 2.		
    fuselage.seat_pitch  	                = 3.		
    fuselage.fineness.nose	                = 0.88 		
    fuselage.fineness.tail	                = 1.13 		
    fuselage.lengths.nose	                = 3.2   * Units.feet	
    fuselage.lengths.tail	                = 6.4 	* Units.feet
    fuselage.lengths.cabin	                = 6.4 	* Units.feet	
    fuselage.lengths.total	                = 16.0 	* Units.feet	
    fuselage.width	                        = 5.85  * Units.feet	
    fuselage.heights.maximum	                = 4.65  * Units.feet		
    fuselage.heights.at_quarter_length	        = 3.75  * Units.feet 	
    fuselage.heights.at_wing_root_quarter_chord	= 4.65  * Units.feet	
    fuselage.heights.at_three_quarters_length	= 4.26  * Units.feet	
    fuselage.areas.wetted	                = 236.  * Units.feet**2	
    fuselage.areas.front_projected	        = 0.14  * Units.feet**2	  	
    fuselage.effective_diameter 	        = 5.85  * Units.feet 	
    fuselage.differential_pressure	        = 0.	
    
    # Segment 	
    segment = SUAVE.Components.Fuselages.Segment() 
    segment.tag			                = 'segment_1'		
    segment.origin	                        = [0., 0. ,0.]		
    segment.percent_x_location	                = 0.		
    segment.percent_z_location	                = 0.0	
    segment.height		                = 0.1   * Units.feet 		
    segment.width		                = 0.1	* Units.feet 	 		
    segment.length		                = 0.		
    segment.effective_diameter	                = 0.1	* Units.feet 		
    fuselage.Segments.append(segment)  
                          
    # Segment 
    segment = SUAVE.Components.Fuselages.Segment()
    segment.tag			                = 'segment_2'		
    segment.origin		                = [4.*0.3048 , 0. ,0.1*0.3048 ] 	
    segment.percent_x_location	                = 0.25 	
    segment.percent_z_location	                = 0.05 
    segment.height		                = 3.75  * Units.feet 
    segment.width		                = 5.65  * Units.feet 	
    segment.length		                = 3.2   * Units.feet 	
    segment.effective_diameter	                = 5.65 	* Units.feet 
    fuselage.Segments.append(segment)  
                          
    # Segment 
    segment = SUAVE.Components.Fuselages.Segment()
    segment.tag			                =' segment_3'		
    segment.origin		                = [8.*0.3048 , 0. ,0.34*0.3048 ] 	
    segment.percent_x_location	                = 0.5 	
    segment.percent_z_location	                = 0.071 
    segment.height		                = 4.65  * Units.feet	
    segment.width		                = 5.55  * Units.feet 	
    segment.length		                = 3.2   * Units.feet
    segment.effective_diameter	                = 5.55  * Units.feet 
    fuselage.Segments.append(segment)  
                          
    # Segment 	
    segment = SUAVE.Components.Fuselages.Segment()
    segment.tag			                = 'segment_4'		
    segment.origin		                = [12.*0.3048 , 0. ,0.77*0.3048 ] 
    segment.percent_x_location	                = 0.75 
    segment.percent_z_location	                = 0.089 	
    segment.height		                = 4.73  * Units.feet		
    segment.width		                = 4.26  * Units.feet 		
    segment.length		                = 3.2   * Units.feet 	
    segment.effective_diameter	                = 4.26  * Units.feet 
    fuselage.Segments.append(segment)  
                          
    # Segment
    segment = SUAVE.Components.Fuselages.Segment()
    segment.tag			                = 'segment_5'		
    segment.origin		                = [16.*0.3048 , 0. ,2.02*0.3048 ] 
    segment.percent_x_location	                = 1.0
    segment.percent_z_location	                = 0.158 
    segment.height		                = 0.67	* Units.feet
    segment.width		                = 0.33	* Units.feet
    segment.length		                = 3.2   * Units.feet	
    segment.effective_diameter	                = 0.33  * Units.feet
    fuselage.Segments.append(segment)  

    # add to vehicle
    vehicle.append_component(fuselage)   
       
    #------------------------------------------------------------------
    # PROPULSOR
    #------------------------------------------------------------------
    net = Vectored_Thrust()
    net.number_of_engines         = 6
    net.thrust_angle              = 90. * Units.degrees
    net.nacelle_diameter          = 0.6 * Units.feet	# need to check	
    net.engine_length             = 0.5 * Units.feet
    net.areas                     = Data()
    net.areas.wetted              = np.pi*net.nacelle_diameter*net.engine_length + 0.5*np.pi*net.nacelle_diameter**2    
    net.voltage                   =  500.

    #------------------------------------------------------------------
    # Design Electronic Speed Controller 
    #------------------------------------------------------------------
    esc                          = SUAVE.Components.Energy.Distributors.Electronic_Speed_Controller()
    esc.efficiency               = 0.95
    net.esc                      = esc
    
    #------------------------------------------------------------------
    # Design Payload
    #------------------------------------------------------------------
    payload                      = SUAVE.Components.Energy.Peripherals.Avionics()
    payload.power_draw           = 0.
    payload.mass_properties.mass = 200. * Units.kg
    net.payload                  = payload

    #------------------------------------------------------------------
    # Design Avionics
    #------------------------------------------------------------------
    avionics                     = SUAVE.Components.Energy.Peripherals.Avionics()
    avionics.power_draw          = 200. * Units.watts
    net.avionics                 = avionics

    #------------------------------------------------------------------
    # Design Battery
    #------------------------------------------------------------------
    bat                          = SUAVE.Components.Energy.Storages.Batteries.Constant_Mass.Lithium_Ion()
    bat.specific_energy          = 350. * Units.Wh/Units.kg
    bat.resistance               = 0.005
    bat.max_voltage              = net.voltage     
    bat.mass_properties.mass     = 300. * Units.kg
    initialize_from_mass(bat, bat.mass_properties.mass)
    net.battery                  = bat

    #------------------------------------------------------------------
    # Design Rotors  
    #------------------------------------------------------------------ 
    rot                         = SUAVE.Components.Energy.Converters.Rotor()
    rot.tag                     = 'Rotors'
    rot.tip_radius              = 3.95  * Units.feet
    rot.hub_radius              = 0.6  * Units.feet
    rot.number_blades           = 3
    rot.freestream_velocity     = 500. * Units['ft/min']
    tip_speed                   = 0.7*343 
    rot.angular_velocity        = tip_speed/rot.tip_radius   
    rot.design_Cl               = 0.8
    rot.design_altitude         = 1000 * Units.feet                   
    rot.design_thrust           = (vehicle.mass_properties.takeoff*9.81/net.number_of_engines)*2.
    rot                         = propeller_design(rot)  

    vehicle_weight              = vehicle.mass_properties.takeoff*9.81    
    rho                         = 1.225
    A                           = np.pi*(rot.tip_radius**2)
    rot.induced_hover_velocity  = np.sqrt(vehicle_weight/(2*rho*A*net.number_of_engines)) 
    rot.origin                  = []
    
    # propulating propellers on the other side of the vehicle    
    for fuselage in vehicle.fuselages:
        if fuselage.tag == 'fuselage':
            continue
        else:
            rot.origin.append(fuselage.origin[0])           
   
    # append propellers to vehicle           
    net.propeller                     = rot
    
    #------------------------------------------------------------------
    # Design Motors
    #------------------------------------------------------------------
    # Motor
    motor = SUAVE.Components.Energy.Converters.Motor() 
    motor.efficiency              = 0.95  
    motor.nominal_voltage         = bat.max_voltage 
    motor.mass_properties.mass    = 3. * Units.kg 
    motor.origin                  = rot.origin  
    motor.propeller_radius        = rot.tip_radius  
    motor.gear_ratio              = 1.0
    motor.gearbox_efficiency      = 1.0 
    motor.no_load_current         = 4.0     
    motor                         = compute_optimal_motor_parameters(motor,rot)
    net.motor               = motor
    

    # append motor origin spanwise locations onto wing data structure 
    motor_origins = np.array(rot.origin)   
    
    # Define motor sizing parameters     
    max_power  = rot.design_power * 1.2
    max_torque = rot.design_torque * 1.2
    
    # test high temperature superconducting motor weight function 
    mass = hts_motor(max_power) 
    
    # test NDARC motor weight function 
    mass = nasa_motor(max_torque)
    
    # test air cooled motor weight function 
    mass = air_cooled_motor(max_power)
    
    motor.mass_properties.mass = mass 
    net.motor                  = motor

    # append motor origin spanwise locations onto wing data structure 
    motor_origins = np.array(rot.origin) 
    vehicle.append_component(net)
    
    vehicle.weight_breakdown = empty(vehicle)
    return vehicle


# ----------------------------------------------------------------------
#   Define the Configurations
# ---------------------------------------------------------------------

def configs_setup(vehicle):
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