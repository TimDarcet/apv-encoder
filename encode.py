#!/usr/bin/env python3

import click
from pathlib import Path
import subprocess
import datetime
from time import sleep
import sys


FFMPEG = Path("ffmpeg").resolve()
FFPROBE = Path("ffprobe").resolve()
PASS_1_QUALITY = 28
AUDIO_BITRATE = 192 * 10 ** 3

@click.command()
@click.option(
    '-f',
    "--folder-to-encode",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True
    ),
    required=True,
    help="Path to folder to be encoded using ffmpeg"
)
@click.option(
    '-s',
    "--target-size",
    type=int,
    required=True,
    help="Target size of the encoded folder, in MB"
)
@click.option(
    '-c',
    "--computers-file",
    type=click.File(),
    default="~/computers_name",
    help="A file containing the ssh connection addresses of the other computers to distribute on"
)
def encode(folder_to_encode, target_size, computers_file):
    """
    Encodes the folder down to the target size
    Distributes the calculation to computers through ssh
    In order to be encoded using a coefficient, \
        files should be placed in folders containing a file named '.coef' and \
        containing a single integer.
    There should be programs (or links to ones) named ffmpeg and ffprobe in the cwd.
    """
    ##### Encoding number 1 #####
    folder_to_encode = Path(folder_to_encode).resolve()
    target_size *= 10 ** 6
    # Read computer list
    computers = list(map(str.strip, computers_file.readlines()))
    cmpidx = 0
    # Make folders
    output_1_folder = folder_to_encode.parent / 'constant_quality_ouput'
    output_1_folder.mkdir(exist_ok=True)
    locks_folder = Path.cwd() / 'locks'
    locks_folder.mkdir(exist_ok=True)
    # logs_folder = Path.cwd() / 'logs'
    # logs_folder.mkdir(exist_ok=True)
    for video in folder_to_encode.rglob('*.mp4'):
        # Create parent folders
        out_folder = output_1_folder / video.parent.relative_to(folder_to_encode)
        out_folder.mkdir(exist_ok=True, parents=True)
        # Get a computer
        cmp = computers[cmpidx % len(computers)]
        cmpidx += 1
        # Launch actual encoding
        cmd_output = subprocess.Popen([
            "ssh",
            "-oStrictHostKeyChecking=no",
            cmp,
            "cd {cwd} \
            && touch {lockfile} \
            && {ffmpeg} -i {invid} -c:v libx264 -preset medium -crf {quality} \
                -pix_fmt yuv420p -threads 0 -c:a copy -y {outvid} \
            && rm -f {lockfile}"\
            .format(
                cwd=Path.cwd().as_posix(),
                lockfile=(Path("./locks") / cmp.split('@')[-1]).as_posix(),
                ffmpeg=FFMPEG,
                invid=video.as_posix(),
                quality=PASS_1_QUALITY,
                outvid=(out_folder / video.name).as_posix()
            )
        ],
        stdout=sys.stdout, stderr=sys.stderr)
        # stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("[{}] encodage n°1 de {} lancé sur {}."\
              .format(datetime.datetime.now().strftime("%H:%M:%S"), video, cmp))
    print(("====================================================\n"
         + "[{}] encodages n°1 (qualité constante) de {} lancés.\n"
         + "====================================================\n")\
           .format(datetime.datetime.now().strftime("%H:%M:%S"),
                   folder_to_encode))
    # Wait for encodings 1 to end
    sleep(2)
    n_remaining = len(list(locks_folder.glob('*')))
    while n_remaining > 0:
        print("[{}] {} encodings in progress, waiting   \b\b\b"\
              .format(datetime.datetime.now().strftime("%H:%M:%S"),
                      n_remaining),
              end='', flush=True)
        sleep(1)
        print('.', end='', flush=True)
        sleep(1)
        print('.', end='', flush=True)
        sleep(1)
        print('.', end='\r', flush=True)
        # print(cmd_output.stdout.readline())
        # print(cmd_output.stderr.read())
        n_remaining = len(list(locks_folder.glob('*')))
    print(("\n====================================================\n"
         + "[{}] encodage n°1 (qualité constante) de {} terminé.\n"
         + "====================================================\n")\
           .format(datetime.datetime.now().strftime("%H:%M:%S"),
                   folder_to_encode))


    ##### Read encoding 1 sizes #####
    sum_sizes = 0
    for video in folder_to_encode.rglob('*.mp4'):
        out_file = output_1_folder / video.relative_to(folder_to_encode)
        # Read coef
        coef = int((video.parent / '.coef').read_text().strip())
        # Check if the encoding 1 worked
        if (not out_file.is_file()):
            raise ValueError("Could not find output of first encoding for {}"\
                             .format(out_file))
        cmd_out = subprocess.run([
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=size",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            out_file.as_posix()
        ])
        sum_sizes += coef * int(cmd_out.stdout) 
    
 
    ##### Do encoding 2 (two-pass actual encoding) #####
    # Make folders
    output_2_folder = folder_to_encode.parent / 'encoding_final_output'
    output_2_folder.mkdir(exist_ok=True)
    for video in folder_to_encode.rglob('*.mp4'):
        # Check if the encoding 1 worked
        if (not out_file.is_file()):
            raise ValueError("Could not find output of first encoding for {}"\
                             .format(out_file))
        # Create parent folders
        out_folder = output_2_folder / video.parent.relative_to(folder_to_encode)
        out_folder.mkdir(exist_ok=True, parents=True)
        # Get a computer
        cmp = computers[cmpidx % len(computers)]
        cmpidx += 1
        # Read coef
        coef = int((video.parent / '.coef').read_text().strip())
        # Calculate bitrate
        out_1_file = output_1_folder / video.relative_to(folder_to_encode)
        c_bitrate_cmd_out = subprocess.run([
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=bit_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            out_1_file
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        c_bitrate = int(c_bitrate_cmd_out.stdout)
        nice_bitrate = target_size * c_bitrate / sum_sizes - AUDIO_BITRATE # TODO: coefs
        # Launch actual encoding
        cmd_output = subprocess.Popen([
            "ssh",
            "-oStrictHostKeyChecking=no",
            cmp,
            "cd {cwd} \
            && touch {lockfile} \
            && ./two_pass_one_file.sh {invid} {outvid} {v_bitrate} {a_bitrate}\
            && rm -f {lockfile}"\
            .format(
                cwd=Path.cwd().as_posix(),
                lockfile=(Path("./locks") / cmp.split('@')[-1]).as_posix(),
                invid=video.as_posix(),
                outvid=(out_folder / video.name).as_posix(),
                v_bitrate=nice_bitrate,
                a_bitrate=AUDIO_BITRATE
            )
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("[{}] encodage n°2 de {} lancé sur {}."\
              .format(datetime.datetime.now().strftime("%H:%M:%S"), video, cmp))
    
    # Clean
    locks_folder.rmdir()


if __name__ == '__main__':
    encode()
