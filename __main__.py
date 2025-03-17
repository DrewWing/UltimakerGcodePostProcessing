# OrcaSlicer to Ultimaker Gcode
# v2.0.0
# Created by Drew Wingfield on March 6th, 2025

# Description:
# This script turns OrcaSlicer's output gcode into Ultimaker-compatible gcode.
# Tested on Ultimaker S5 and OrcaSlicer v2.2.0

# Current issues:
# 1. The machine heats up both extruders when only one is needed. There seems to be no difference in the gcode???
# 2. [SOLVED] The "time remaining" display on the machine while printing is broken. It just shows 0m00s
#      Solve via this script - get the line OrcaSlicer spits out near the bottom "; estimated printing time (normal mode) = 12d 6h 22m 24s", 
#      do the math to convert it to seconds, then replace it in the header.



__version__ = "2.0.0"

import os
from os import getenv, path
import sys
import ntpath

DEBUG = False # If true, adds a bunch of info to the gcode file for debug

START_CODE = ";DREW_ORCASLICER_TO_ULTIMAKER_GCODE_START\n"
# The start code before the Ultimaker-specific starting code. This does not appear in the final gcode file.

CUSTOM_FOOTER = """; The below gcode is needed for Ultimakers to recognize the file.
;End of Gcode
;SETTING_3 {"global_quality": "[general]\\\\nversion = 4\\\\nname = FEDC Default\\\\nd
;SETTING_3 efinition = ultimaker_s5\\\\n\\\\n[metadata]\\\\ntype = quality_changes\\\\nq
;SETTING_3 uality_type = draft\\\\nsetting_version = 23\\\\n\\\\n[values]\\\\nsupport_en
;SETTING_3 able = False\\\\n\\\\n", "extruder_quality": ["[general]\\\\nversion = 4\\\\n
;SETTING_3 name = FEDC Default\\\\ndefinition = ultimaker_s5\\\\n\\\\n[metadata]\\\\ntyp
;SETTING_3 e = quality_changes\\\\nquality_type = draft\\\\nintent_category = defaul
;SETTING_3 t\\\\nposition = 0\\\\nsetting_version = 23\\\\n\\\\n[values]\\\\nprime_blob_en
;SETTING_3 able = True\\\\n\\\\n", "[general]\\\\nversion = 4\\\\nname = FEDC Default\\\\n
;SETTING_3 definition = ultimaker_s5\\\\n\\\\n[metadata]\\\\ntype = quality_changes\\\\n
;SETTING_3 quality_type = draft\\\\nintent_category = default\\\\nposition = 1\\\\nset
;SETTING_3 ting_version = 23\\\\n\\\\n[values]\\\\n\\\\n"]}
"""



# Clear the error writer
with open("orcaslicer_to_ultimaker_gcode_ERRORS.log", "a") as err_writer:
    err_writer.truncate()



def convert_to_seconds(total):
    seconds_total = 0
    
    for item in total.strip().split(" "):
        item = item.strip()
        if item.endswith("s"):
            seconds_total += int(item[:-1])
            
        elif item.endswith("m"):
            seconds_total += int(item[:-1])*60
            
        elif item.endswith("h"):
            seconds_total += int(item[:-1])*3600
        
        elif item.endswith("d"):
            seconds_total += int(item[:-1])*3600*24
           
    
    return str(int(seconds_total))



def write_err(err):
    with open("orcaslicer_to_ultimaker_gcode_ERRORS.log", "a") as err_writer:
        err_writer.write(str(err))
        

env_slicer_pp_output_name = str(getenv("SLIC3R_PP_OUTPUT_NAME", "DefaultExport.gcode"))
input_name = str(sys.argv[-1])

if ".gcode" not in input_name.lower():
    input_name = env_slicer_pp_output_name

try:
    print("Converting gcode...")
    
    # First read all lines from source file
    with open(input_name,mode="r") as reader:
        all_lines = reader.readlines()

    total_time = 0
    
    # Iterate backwards to save time, it's near the end of the file anyway
    for line in all_lines[::-1]:
        if line.strip().startswith("; estimated printing time (normal mode) ="):
            total_time = convert_to_seconds(line.replace("; estimated printing time (normal mode) =",""))
            break
    
    # Then process the lines to the source file
    with open(input_name, mode='w', encoding='UTF-8') as writer:
        writer.truncate() # Make 100% sure that the file is empty
        
        if DEBUG:
            # Write debug stuff
            writer.write(f"orcaslicer_to_ultimaker_gcode.py v{__version__} DEBUG mode enabled. \n")
            writer.write(f"all arguments: {sys.argv}\n")
            writer.write(f"input name: {input_name}\n")
            writer.write(f"env slicer name: {env_slicer_pp_output_name} \n")
            writer.write(f"total time of print in seconds: {total_time}\n")
        
        counter = 0
        write_counter = 0
        # Write all gcode after the special start code
        # Because Ultimaker only accepts gcode that starts with their script.
        
        disable_writer = True
            
        if DEBUG:
            writer.write("DEBUG: Going through lines now.\n")
            writer.write(f"DEBUG: length of lines: {len(all_lines)}\n")
            
        for line in all_lines:
            counter += 1
            if disable_writer and str(line).upper().strip() == START_CODE.upper().strip():
                disable_writer = False
                if DEBUG:
                    writer.write("DEBUG: Writer no longer disabled.\n")
                
            elif not disable_writer:
                write_counter += 1
                
                if line.strip().startswith(";PRINT.TIME:1"):
                    writer.write(f";PRINT.TIME:{int(total_time)}\n")
                
                else:
                    writer.write(line)
                
        try:
            assert counter > 0
            assert write_counter > 0
            assert disable_writer == False
        
        except AssertionError as e:
            writer.write(str(e))
            counter = 0
            for line in reader:
                counter += 1
                writer.write(line)
                
                if counter > 30:
                    raise e
                
            raise e

        # Write the custom footer. If Ultimaker machines don't see this, they freak out
        # and will refuse to print the file.
        writer.write(CUSTOM_FOOTER)
            
            
    
    # Finally, create the needed file for OrcaSlicer with the correct name
    # This bit was copied from the example script at https://github.com/foreachthing/Slic3rPostProcessing/blob/a47d64c8b83459cf3bd2906a3e81172c07328f34/SPP-Python/Slic3rPostProcessor.py
    # get envvar from PrusaSlicer
    env_slicer_pp_output_name = str(
        getenv('SLIC3R_PP_OUTPUT_NAME'))

    current_file_index = 0 # This script doesn't have the capability to do multiple files yet.
    
    # create file for PrusaSlicer with correct name as content
    with open(input_name + '.output_name', mode='w', encoding='UTF-8') as fopen:
        fopen.write(#str(current_file_index) + '_' +
            ntpath.basename(env_slicer_pp_output_name))
        
        

except (FileNotFoundError, IsADirectoryError) as err:
    print(err)
    write_err("Some kind of file or directory error occured!")
    write_err(err)
    raise err
    
    
except Exception as err:
    print(err)
    write_err("An error occured!\n")
    write_err(err)
    write_err("\n\n")
    raise err


