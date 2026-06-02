# THESE FUNCTIONS CALCULATE AND PRINT THE PRESSURE DROPS BY HAND ACROSS THE CHANNELS IN THE CHIP TO VERIFY AND COMPARE AGAINST THE MODIFIED NODAL ANALYSIS (MNA)
# TODO add the media 2 inflow and the adapted outflow of each organ module

def calculate_pressure_drop_in_meshes(channels, no_of_modules_x, no_of_modules_y, viscosity): 
    '''
    Calculate the pressure drops in connecthe channels (meshes) by hand based on Kirchhoff's voltage law.
    Should be redundant after the modified nodal analysis (MNA).
    '''
    pressure_drop_organ_module = channels[f"organ_channel_top_A0"].calculate_pressure_drop(viscosity) 
    for i in range(no_of_modules_x - 1):
        # between each module we have a closed cycle of channels where we need to apply Kirchhoff's voltage law, once i>1 more meshes are located between the modules

        # PRESSURE DROP BETWEEN 2 MODULES IN X DIRECTION - conc x and y
        if i == 0:
            seg_nr = i + 2
        else:
            seg_nr = i * 2

        pressure_drop_clockwise_x = (
            channels[f"conc_x_seg_{seg_nr - 1}"].calculate_pressure_drop(viscosity) + 
            channels[f"conc_x_seg_{seg_nr}"].calculate_pressure_drop(viscosity) + 
            channels[f"conc_x_{chr(65 + i + 1)}{no_of_modules_y - 1}"].calculate_pressure_drop(viscosity)
        )
        for j in range(no_of_modules_y):
            pressure_drop_clockwise_x += channels[f"conc_x_branch_{chr(65 + i + 1)}{j}"].calculate_pressure_drop(viscosity)

    
        pressure_drop_anticlockwise_x = (
            channels[f"conc_x_branch_{chr(65 + i)}{0}"].calculate_pressure_drop(viscosity) + 
            channels[f"conc_x_{chr(65 + i)}{0}"].calculate_pressure_drop(viscosity)
        )

        # pressure_drop_clockwise_y = (
        #     channels[f"conc_y_branch_{chr(65 + i)}{0}"].calculate_pressure_drop(viscosity) + 
        #     channels[f"conc_y_{chr(65 + i)}{0}"].calculate_pressure_drop(viscosity)
        # )


        # pressure_drop_anticlockwise_y = ( # TODO just copied this here
        #     channels[f"conc_y_{chr(65 + i)}{0}"].calculate_pressure_drop(viscosity)
        # )


        pressure_drop_clockwise_rest = (
            channels[f"organ_channel_inflow_{chr(65 + i + 1)}{no_of_modules_y - 1}"].calculate_pressure_drop(viscosity) +
            pressure_drop_organ_module +
            channels[f"organ_channel_outflow_2{chr(65 + i + 1)}{no_of_modules_y - 1}"].calculate_pressure_drop(viscosity) +
            channels[f"organ_channel_outflow_{chr(65 + i + 1)}{no_of_modules_y - 1}"].calculate_pressure_drop(viscosity) + 
            channels[f"outflow_{chr(65 + i + 1)}{no_of_modules_y - 1}"].calculate_pressure_drop(viscosity)
        )
        
        pressure_drop_anticlockwise_rest = (
            channels[f"organ_channel_inflow_{chr(65 + i)}{0}"].calculate_pressure_drop(viscosity) + 
            pressure_drop_organ_module + 
            channels[f"organ_channel_outflow_2{chr(65 + i)}{0}"].calculate_pressure_drop(viscosity) + 
            channels[f"organ_channel_outflow_{chr(65 + i)}{0}"].calculate_pressure_drop(viscosity) + 
            channels[f"chip_outflow_{i}"].calculate_pressure_drop(viscosity)
        )

        for j in range(no_of_modules_y):
            pressure_drop_anticlockwise_rest += channels[f"outflow_{chr(65 + i)}{j}"].calculate_pressure_drop(viscosity)

        # Relationship between the pressure drops in the x and y direction IF THERE ARE NO Y MODULES THIS IS NOT NECESSARY (CALCULATES THE SAME PRESSURE CYCLES AS ABOVE)
        # print("pressure drop clockwise x:", pressure_drop_clockwise_x)
        # print("pressure drop anticlockwise x:", pressure_drop_anticlockwise_x)
        # # print("pressure drop clockwise y:", pressure_drop_clockwise_y)
        # # print("pressure drop anticlockwise y:", pressure_drop_anticlockwise_y)
        # print("pressure drop clockwise rest:", pressure_drop_clockwise_rest)
        # print("pressure drop anticlockwise rest:", pressure_drop_anticlockwise_rest)

        print("These should be equal:", pressure_drop_clockwise_x + pressure_drop_clockwise_rest, pressure_drop_anticlockwise_x + pressure_drop_anticlockwise_rest)


    # PRESSURE DROP BETWEEN 2 MODULES IN Y DIRECTION - conc x and y
    for i in range(no_of_modules_x):
        for j in range(no_of_modules_y - 1): # between 2 modules in y-direction for each column of modules in x-direction
            pressure_drop_clockwise_x = (
                channels[f"conc_x_{chr(65 + i)}{j}"].calculate_pressure_drop(viscosity)
            )
            pressure_drop_anticlockwise_x = (
                channels[f"conc_x_branch_{chr(65 + i)}{j + 1}"].calculate_pressure_drop(viscosity) + 
                channels[f"conc_x_{chr(65 + i)}{j + 1}"].calculate_pressure_drop(viscosity)
            )

            pressure_drop_clockwise_y = (
                channels[f"conc_y_{chr(65 + i)}{j}"].calculate_pressure_drop(viscosity)
            )

            if j == 0:
                seg_nr = j + 2
            else:
                seg_nr = j * 2
            
            pressure_drop_anticlockwise_y = (
                channels[f"conc_y_seg_{seg_nr - 1}"].calculate_pressure_drop(viscosity) + 
                channels[f"conc_y_seg_{seg_nr}"].calculate_pressure_drop(viscosity) + 
                channels[f"conc_y_{chr(65 + i)}{j + 1}"].calculate_pressure_drop(viscosity)
            )

            for m in range(i + 1): # TODO double check if we actually want to do this this way, alternatively we could take the modules in the x-direction -1 
                pressure_drop_clockwise_y += (
                    channels[f"conc_y_branch_{chr(65 + m)}{j}"].calculate_pressure_drop(viscosity)
                )
                pressure_drop_anticlockwise_y += (
                    channels[f"conc_y_branch_{chr(65 + m)}{j + 1}"].calculate_pressure_drop(viscosity)
                )
                
            pressure_drop_clockwise_rest = (
                channels[f"organ_channel_inflow_{chr(65 + i)}{j}"].calculate_pressure_drop(viscosity) + 
                pressure_drop_organ_module + 
                channels[f"organ_channel_outflow_{chr(65 + i)}{j}"].calculate_pressure_drop(viscosity) + 
                channels[f"organ_channel_outflow_2{chr(65 + i)}{j}"].calculate_pressure_drop(viscosity) + 
                channels[f"outflow_{chr(65 + i)}{j}"].calculate_pressure_drop(viscosity)
            )

            pressure_drop_anticlockwise_rest = (
                channels[f"organ_channel_inflow_{chr(65 + i)}{j + 1}"].calculate_pressure_drop(viscosity) + 
                pressure_drop_organ_module + 
                channels[f"organ_channel_outflow_{chr(65 + i)}{j + 1}"].calculate_pressure_drop(viscosity) + 
                channels[f"organ_channel_outflow_2{chr(65 + i)}{j + 1}"].calculate_pressure_drop(viscosity)
            )

            print("These should be equal:", pressure_drop_clockwise_x + pressure_drop_clockwise_rest, pressure_drop_anticlockwise_x + pressure_drop_anticlockwise_rest)

        # print("pressure drop clockwise x:", pressure_drop_clockwise_x)
        # print("pressure drop anticlockwise x:", pressure_drop_anticlockwise_x)
        # print("pressure drop clockwise y:", pressure_drop_clockwise_y)
        # print("pressure drop anticlockwise y:", pressure_drop_anticlockwise_y)
        # print("pressure drop clockwise rest:", pressure_drop_clockwise_rest)
        # print("pressure drop anticlockwise rest:", pressure_drop_anticlockwise_rest)

    # PRESSURE DROP FOR THE MEDIA SUPPLY
    # pressure cycle if there is only one media inlet, between the media reservoir and the organ_channel_inflow of the first module A0
    # TODO does this even make sense? because one of the channels goes the wrong direction
    for i in range(1, no_of_modules_x -1):
        pressure_drop_clockwise_media_x = (
            channels[f"media_feed_x_{i}"].calculate_pressure_drop(viscosity) + 
            channels[f"media_feed_x_{i}"].calculate_pressure_drop(viscosity)
        )
        pressure_drop_anticlockwise_media_x = (
            channels[f"media_feed_x_{i - 1}"].calculate_pressure_drop(viscosity) + 
            channels[f"conc_x_seg_{i * 2}"].calculate_pressure_drop(viscosity) + 
            channels[f"conc_x_seg_{i * 2 + 1}"].calculate_pressure_drop(viscosity)
        )

        print("These should be equal:", pressure_drop_clockwise_media_x, pressure_drop_anticlockwise_media_x) 
              
    for j in range(1, no_of_modules_y - 1):
        pressure_drop_clockwise_media_y =  (
            channels[f"media_feed_y_{j}"].calculate_pressure_drop(viscosity) + 
            channels[f"media_feed_y_{j}"].calculate_pressure_drop(viscosity)
        )
        pressure_drop_anticlockwise_media_y = (
            channels[f"media_feed_y_{j - 1}"].calculate_pressure_drop(viscosity) + 
            channels[f"conc_y_seg_{j * 2}"].calculate_pressure_drop(viscosity) + 
            channels[f"conc_y_seg_{j * 2 + 1}"].calculate_pressure_drop(viscosity)
        )

        print("These should be equal:", pressure_drop_clockwise_media_y, pressure_drop_anticlockwise_media_y)

   
def print_node_and_channel_pressures(nodes, channels, viscosity):
    """
    Prints the pressure at each node and the pressure drop across each channel.
    """
    print("\nNode Pressures:")
    print(f"{'Node':<25} {'Pressure (Pa)':<20}")
    print("=" * 50)

    for name, node in nodes.items():
        print(f"{name:<25} {node.pressure:<20.5f}")

    print("\nChannel Pressure Drops:")
    print(f"{'Channel':<30} {'Node1':<20} {'Node2':<20} {'ΔP (Pa)':<20}")
    print("=" * 90)

    for name, channel in channels.items():
        P1 = nodes[channel.node1].pressure
        P2 = nodes[channel.node2].pressure
        pressure_drop = P1 - P2  # ΔP = P1 - P2

        print(f"{name:<30} {channel.node1:<20} {channel.node2:<20} {pressure_drop:<20.5f}")
