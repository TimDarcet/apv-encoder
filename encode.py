#!/usr/bin/env python3

import click
from pathlib import Path
import subprocess
import datetime


FFMEPG = "~/ffmpeg-static/ffmpeg"
FFMPEG = "~/ffmpeg-static/ffprobe"
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
    folder_to_encode = Path(folder_to_encode).resolve()
    target_size *= 10 ** 6
    # Read computer list
    computers = list(computers_file.readlines())
    cmpidx = 0
    # Make folders
    output_1_folder = folder_to_encode.parent / 'constant_quality_ouput'
    output_1_folder.mkdir(exist_ok=True)
    locks_folder = Path.cwd() / 'locks'
    locks_folder.mkdir(exist_ok=True)
    for video in folder_to_encode.rglob('*.mp4'):
        print(video)
        out_folder = output_1_folder / video.parent.relative_to(folder_to_encode)
        out_folder.mkdir(exist_ok=True, parents=True)
        cmp = computers[cmpidx]
        cmpidx += 1
        cmd_output = subprocess.run([
            "ssh",
            "-oStrictHostKeyChecking=no",
            cmp,
            "cd {cwd} \
            && touch {lockfile} \
            && {ffmpeg} -i {invid} -c:v libx264 -preset medium -crf {quality} \
                -pix_fmt yuv420p -threads 0 -c:a copy -y {outvid} \
            && rm -f {lockfile}"\
            .format(
                cwd=Path.cwd(),
                lockfile=Path("./locks") / cmp.split('@')[-1],
                ffmpeg=FFMPEG,
                invid=video,
                quality=PASS_1_QUALITY,
                outvid=out_folder / video.name
            )
        ])
        print("[{}] encodage n°1 de {} lancé sur {}."\
            .format(datetime.datetime.now().strftime("%H:%M:%S"), video, cmp))
     

        
        

if __name__ == '__main__':
    encode()
