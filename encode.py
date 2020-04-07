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
@click.option(
    '-t',
    "--max-threads",
    type=int,
    default=0,
    help="Maximum simultaneous threads on a single computer (useful if low number of computers). 0 disables the limit. Default : 0"
)
def encode(folder_to_encode, target_size, computers_file, ffmpeg_path, ffprobe_path, max_threads):
    """
    Encodes the folder down to the target size
    Distributes the calculation to computers through ssh
    In order to be encoded using a coefficient, \
        files should be placed in folders containing a file named '.coef' and \
        containing a single integer.
    There should be programs (or links to ones) named ffmpeg and ffprobe in the cwd.
    """

    ##### Read input #####
    folder_to_encode = Path(folder_to_encode).resolve()
    target_size *= 10 ** 6
    # Read computer list
    computers = list(map(str.strip, computers_file.readlines()))
    videos_on_computer = {computer:[] for computer in computers}


    ##### Initial checks #####
    for video in folder_to_encode.rglob("*.mp4"):
        getVideoCoeff(video) #raise an error if coef does not exist


    ##### Prepare work environment #####
    # Make an empty lock folder
    locks_folder = Path.cwd() / 'locks'
    locks_folder.mkdir(exist_ok=True)
    for sub in locks_folder.iterdir() :
        sub.unlink()
    # get list of videos
    videos_to_encode = list(folder_to_encode.rglob("*.mp4"))
    nb_videos_to_encode = len(videos_to_encode)



    ##### Do encoding 1 #####
    printStep("Step 1 : First encoding")
    # Make folders
    output_1_folder = folder_to_encode.parent / 'constant_quality_output'
    output_1_folder.mkdir(exist_ok=True)
    current_encodings = 0
    index_next_video_to_encode = 0
    while current_encodings + nb_videos_to_encode - index_next_video_to_encode > 0:
        if index_next_video_to_encode < nb_videos_to_encode:
            for cmp in computers:
                if getNbLocksOfComputer(cmp, locks_folder) < max_threads and index_next_video_to_encode < nb_videos_to_encode:
                    video = videos_to_encode[index_next_video_to_encode]
                    # Create parent folders
                    out_folder = output_1_folder / video.parent.relative_to(folder_to_encode)
                    out_folder.mkdir(exist_ok=True, parents=True)
                    # Check out file
                    out_file = out_folder / video.name
                    if not out_file.is_file():
                        # Launch actual encoding
                        lockfile = getLock(video, cmp)
                        subprocess.Popen([
                            "ssh",
                            "-oStrictHostKeyChecking=no",
                            cmp,
                            "cd \"{cwd}\" \
                            && {ffmpeg} -loglevel error -hide_banner -i \"{invid}\" -c:v libx264 -preset medium -crf {quality} \
                                -pix_fmt yuv420p -threads 0 -c:a copy -y \"{outvid}\" \
                            && rm -f \"{lockfile}\""\
                            .format(
                                cwd=Path.cwd().as_posix(),
                                lockfile=lockfile,
                                ffmpeg=ffmpeg_path,
                                invid=video.as_posix(),
                                quality=PASS_1_QUALITY,
                                outvid=out_file.as_posix()
                            )
                        ],
                        stdout=sys.stdout, stderr=sys.stderr)
                        printInfo("Encodage n°1 de {} lancé sur {}".format(video, cmp))
                    else:
                        printInfo("Skipped  {}: {} exists.".format(video, out_file))
                    index_next_video_to_encode += 1
        sleep(1)
        current_encodings = len(list(locks_folder.glob('*')))
        printStatus("{} encodings in progress, {} done, {} in queue".format(current_encodings, index_next_video_to_encode - current_encodings, nb_videos_to_encode - index_next_video_to_encode))



    ##### Read encoding 1 sizes #####
    printStep("Step 2 : Reading step 1 results")
    sum_sizes = 0
    for video in videos_to_encode:
        printInfo("Reading {}".format(video))
        out_file = output_1_folder / video.relative_to(folder_to_encode)
        # Read coef
        coef = getVideoCoeff(video)
        # Check if the encoding 1 worked
        if (not out_file.is_file()):
            raise FileNotFoundError("Could not find output of first encoding for {}. Path searched: {}".format(video, out_file))
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



    ##### Do encoding 2 (two-pass actual encoding) #####
    printStep("Step 3 : Second encoding")
    # Make folders
    output_2_folder = folder_to_encode.parent / 'encoding_final_output'
    output_2_folder.mkdir(exist_ok=True)
    current_encodings = 0
    index_next_video_to_encode = 0
    while current_encodings + nb_videos_to_encode - index_next_video_to_encode > 0:
        if index_next_video_to_encode < nb_videos_to_encode:
            for cmp in computers:
                if getNbLocksOfComputer(cmp, locks_folder) < max_threads and index_next_video_to_encode < nb_videos_to_encode:
                    video = videos_to_encode[index_next_video_to_encode]
                    out_1_file = output_1_folder / video.relative_to(folder_to_encode)
                    # Check if the encoding 1 worked
                    if (not out_1_file.is_file()):
                        raise ValueError("Could not find output of first encoding for {}"\
                                         .format(out_file))
                    # Create parent folders
                    out_folder = output_2_folder / video.parent.relative_to(folder_to_encode)
                    out_folder.mkdir(exist_ok=True, parents=True)
                    # Read coef
                    coef = getVideoCoeff(video)
                    # Calculate bitrate
                    cmd_out = subprocess.run([
                        ffprobe_path,
                        "-v",
                        "error",
                        "-show_entries",
                        "format=bit_rate",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        str(out_1_file.as_posix())
                    ], stdout=subprocess.PIPE, stderr=sys.stderr)
                    c_bitrate = int(cmd_out.stdout)
                    nice_bitrate = target_size * c_bitrate * coef / sum_sizes - AUDIO_BITRATE
                    # Launch actual encoding
                    lockfile = getLock(video, cmp)
                    subprocess.Popen([
                        "ssh",
                        "-oStrictHostKeyChecking=no",
                        cmp,
                        "cd \"{cwd}\" \
                        && ./two_pass_one_file.sh \"{invid}\" \"{outvid}\" {v_bitrate} {a_bitrate} \"{ffmpeg}\" \"{ffprobe}\" \
                        && rm -f \"{lockfile}\""\
                        .format(
                            cwd=Path.cwd().as_posix(),
                            lockfile=lockfile,
                            invid=video.as_posix(),
                            outvid=(out_folder / video.name).as_posix(),
                            v_bitrate=nice_bitrate,
                            a_bitrate=AUDIO_BITRATE,
                            ffmpeg=ffmpeg_path,
                            ffprobe=ffprobe_path
                        )
                    ],
                    stdout=subprocess.PIPE, stderr=sys.stderr)
                    print("[{}] encodage n°2 de {} lancé sur {}."\
                          .format(datetime.datetime.now().strftime("%H:%M:%S"), video, cmp))
                    index_next_video_to_encode += 1
        sleep(1)
        current_encodings = len(list(locks_folder.glob('*')))
        printStatus("{} encodings in progress, {} done, {} in queue".format(current_encodings, index_next_video_to_encode - current_encodings, nb_videos_to_encode - index_next_video_to_encode))



    printStep("Done! Cleaning...")
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
    return int(coefpath.read_text().strip())

def printStep(text):
    fullText = "[{}] ".format(datetime.datetime.now().strftime("%H:%M:%S")) + text
    print()
    print("="*len(fullText))
    print(fullText)
    print("="*len(fullText), flush=True)
    print()

def printInfo(text):
    print("[{}]".format(datetime.datetime.now().strftime("%H:%M:%S")), text, flush=True)

def printStatus(text):
    print("[{}]".format(datetime.datetime.now().strftime("%H:%M:%S")), text, end='\r', flush=True)

def getNbLocksOfComputer(cmp, locks_folder):
    return len(list(locks_folder.glob('*@' +  cmp.split('@')[-1])))

def getLock(video, cmp):
    filename = str(video.name) + '@' +  cmp.split('@')[-1]
    lockfile = (Path("./locks") / filename).as_posix()
    subprocess.Popen([
        "touch",
        lockfile
    ])
    return lockfile

if __name__ == '__main__':
    encode()
