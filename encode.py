#!/usr/bin/env python3

import click
from pathlib import Path
import subprocess
import datetime
from time import sleep
import sys
from memoization import cached

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
@click.option(
    '-m',
    "--ffmpeg-path",
    default="ffmpeg",
    help="FFMPEG path. Default : ${whereis ffmpeg}"
)
@click.option(
    '-p',
    "--ffprobe-path",
    default="ffprobe",
    help="FFPROBE path. Default : ${whereis ffprobe}"
)
def encode(folder_to_encode, target_size, computers_file, ffmpeg_path, ffprobe_path):
    """
    Encodes the folder down to the target size
    Distributes the calculation to computers through ssh
    In order to be encoded using a coefficient, \
        files should be placed in folders containing a file named '.coef' and \
        containing a single integer.
    There should be programs (or links to ones) named ffmpeg and ffprobe in the cwd.
    """

    folder_to_encode = Path(folder_to_encode).resolve()
    target_size *= 10 ** 6
    # Read computer list
    computers = list(map(str.strip, computers_file.readlines()))
    cmpidx = 0

    ##### Initial checks #####
    for video in folder_to_encode.rglob("*.mp4")
        getVideoCoeff(video) #raise an error if coef does not exist

    ##### Encoding number 1 #####
    # Make folders
    output_1_folder = folder_to_encode.parent / 'constant_quality_output'
    output_1_folder.mkdir(exist_ok=True)
    locks_folder = Path.cwd() / 'locks'
    locks_folder.mkdir(exist_ok=True)
    for video in folder_to_encode.rglob('*.mp4'):
        # Create parent folders
        out_folder = output_1_folder / video.parent.relative_to(folder_to_encode)
        out_folder.mkdir(exist_ok=True, parents=True)
        # Get a computer
        cmp = computers[cmpidx % len(computers)]
        cmpidx += 1
        # Check out file
        out_file = out_folder / video.name
        if not out_file.is_file():
            # Launch actual encoding
            lock_name = str(video.name) + '@' +  cmp.split('@')[-1]
            cmd_output = subprocess.Popen([
                "ssh",
                "-oStrictHostKeyChecking=no",
                cmp,
                "cd \"{cwd}\" \
                && touch \"{lockfile}\" \
                && {ffmpeg} -i \"{invid}\" -c:v libx264 -preset medium -crf {quality} \
                    -pix_fmt yuv420p -threads 0 -c:a copy -y \"{outvid}\" \
                && rm -f \"{lockfile}\""\
                .format(
                    cwd=Path.cwd().as_posix(),
                    lockfile=(Path("./locks") / lock_name).as_posix(),
                    ffmpeg=ffmpeg_path,
                    invid=video.as_posix(),
                    quality=PASS_1_QUALITY,
                    outvid=out_file.as_posix()
                )
            ],
            stdout=sys.stdout, stderr=sys.stderr)
            # stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # stdout=subprocess.PIPE, stderr=sys.stderr)
            print("[{}] encodage n°1 de {} lancé sur {}."\
                .format(datetime.datetime.now().strftime("%H:%M:%S"), video, cmp))
        else:
            print("[{}] Skipped  {}: {} exists."\
                .format(datetime.datetime.now().strftime("%H:%M:%S"), video, out_file))
    print(("====================================================\n"
         + "[{}] encodages n°1 (qualité constante) de {} lancés.\n"
         + "====================================================\n")\
           .format(datetime.datetime.now().strftime("%H:%M:%S"),
                   folder_to_encode))
    # Wait for encodings 1 to end
    sleep(4)
    n_remaining = len(list(locks_folder.glob('*')))
    while n_remaining > 0:
        print("[{}] {} encodings in progress, waiting     \b\b\b\b\b"\
              .format(datetime.datetime.now().strftime("%H:%M:%S"),
                      n_remaining),
              end='', flush=True)
        sleep(1)
        print('.', end='', flush=True)
        sleep(1)
        print('.', end='', flush=True)
        sleep(1)
        print('.', end='\r', flush=True)
        sleep(1)
        n_remaining = len(list(locks_folder.glob('*')))
    print(("\n====================================================\n"
         + "[{}] encodage n°1 (qualité constante) de {} terminé.\n"
         + "====================================================\n")\
           .format(datetime.datetime.now().strftime("%H:%M:%S"),
                   folder_to_encode))

    sleep(3)
    ##### Read encoding 1 sizes #####
    print("[{}] Lecture des tailles de fichiers"\
          .format(datetime.datetime.now().strftime("%H:%M:%S")))
    sum_sizes = 0
    for video in folder_to_encode.rglob('*.mp4'):
        print("[{}] lecture de {}"\
            .format(datetime.datetime.now().strftime("%H:%M:%S"), video))
        out_file = output_1_folder / video.relative_to(folder_to_encode)
        # Read coef
        coef = getVideoCoeff(video)
        # Check if the encoding 1 worked
        if (not out_file.is_file()):
            raise FileNotFoundError("Could not find output of first encoding for {}. Path searched: {}"\
                             .format(video, out_file))
        cmd_out = subprocess.run([
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=size",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(out_file.as_posix())
        ], stdout=subprocess.PIPE, stderr=sys.stderr)
        sum_sizes += coef * int(cmd_out.stdout)

    print("[{}] Encodage n°2"\
          .format(datetime.datetime.now().strftime("%H:%M:%S")))
    ##### Do encoding 2 (two-pass actual encoding) #####
    # Make folders
    output_2_folder = folder_to_encode.parent / 'encoding_final_output'
    output_2_folder.mkdir(exist_ok=True)
    for video in folder_to_encode.rglob('*.mp4'):
        out_1_file = output_1_folder / video.relative_to(folder_to_encode)
        # Check if the encoding 1 worked
        if (not out_1_file.is_file()):
            raise ValueError("Could not find output of first encoding for {}"\
                             .format(out_file))
        # Create parent folders
        out_folder = output_2_folder / video.parent.relative_to(folder_to_encode)
        out_folder.mkdir(exist_ok=True, parents=True)
        # Get a computer
        cmp = computers[cmpidx % len(computers)]
        cmpidx += 1
        # Read coef
        coef = getVideoCoeff(video)
        # Calculate bitrate
        c_bitrate_cmd_out = subprocess.run([
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=bit_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(out_1_file.as_posix())
        ], stdout=subprocess.PIPE, stderr=sys.stderr)
        c_bitrate = int(c_bitrate_cmd_out.stdout)
        nice_bitrate = target_size * c_bitrate * coef / sum_sizes - AUDIO_BITRATE
        # Launch actual encoding
        lock_name = str(video.name) + '@' +  cmp.split('@')[-1]
        cmd_output = subprocess.Popen([
            "ssh",
            "-oStrictHostKeyChecking=no",
            cmp,
            "cd \"{cwd}\" \
            && touch \"{lockfile}\" \
            && ./two_pass_one_file.sh \"{invid}\" \"{outvid}\" {v_bitrate} {a_bitrate} \"{ffmpeg}\" \"{ffprobe}\" \
            && rm -f \"{lockfile}\""\
            .format(
                cwd=Path.cwd().as_posix(),
                lockfile=(Path("./locks") / lock_name).as_posix(),
                invid=video.as_posix(),
                outvid=(out_folder / video.name).as_posix(),
                v_bitrate=nice_bitrate,
                a_bitrate=AUDIO_BITRATE,
                ffmpeg=ffmpeg_path,
                ffprobe=ffprobe_path
            )
        ],
        # stdout=sys.stdout, stderr=sys.stderr)
        # stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout=subprocess.PIPE, stderr=sys.stderr)
        print("[{}] encodage n°2 de {} lancé sur {}."\
              .format(datetime.datetime.now().strftime("%H:%M:%S"), video, cmp))

    # Wait for encodings 2 to end
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
        n_remaining = len(list(locks_folder.glob('*')))
    print(("\n====================================================\n"
         + "[{}] encodage n°2 (final)  de {} terminé.\n"
         + "====================================================\n")\
           .format(datetime.datetime.now().strftime("%H:%M:%S"),
                   folder_to_encode))

    # Clean
    locks_folder.rmdir()

@cached
def getVideoCoeff(video):
    # Read coef
    coefpath = video.parent / '.coef'
    i = 0
    while not coefpath.is_file():
        coefpath = coefpath.parent.parent / '.coef'
        i += 1
        if i > 100:
            raise FileNotFoundError("Could not find .coef file for {}."\
                .format(video))
    coef = int(coefpath.read_text().strip())

if __name__ == '__main__':
    encode()
