import os
import subprocess
import json
from StreamingServer.settings import customstderr, customstdout

def dash_packager(video_layer_low, low_layer_bitrate, low_layer_height, 
    video_layer_high, high_layer_bitrate, high_layer_resolution, 
    audio_layer, 
    mpd_path):
    '''
    Args:
        
    '''
    command = ["MP4Box", "-dash", "4000", "-frag", "4000", "-rap", \
        "-segment-name", "segment_$RepresentationID$_", "-fps", "24"]

    if video_layer_low:
        command.extend( [f"{video_layer_low}#video:id={low_layer_height}p:#Bitrate={low_layer_bitrate}"])

    if video_layer_high:
        command.extend( [f"{video_layer_high}#video:id={high_layer_resolution}p:#Bitrate={high_layer_bitrate}"])

    if audio_layer:
        command.extend( [f"{audio_layer}#audio:id=English:role=main"] )

    command.extend( ["-out",  f"{mpd_path}"] )

    #print(command)
    #response_json = subprocess.check_output(command, shell=True, stderr=None)

    print("dash package command: {}".format(" ".join(command)))
    completed_process_instance = subprocess.run(command, stdout=customstdout,
                                            stderr=customstderr)
    if completed_process_instance.returncode != 0:
        print("An error occured while running dash_packager subprocess")
        print(completed_process_instance.stderr)
        print(completed_process_instance.stdout)
        raise Exception('dash_packager_error', 'error')

    
