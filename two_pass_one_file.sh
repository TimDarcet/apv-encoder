#!/bin/bash
if [ -z "$6" ]; then
    exit 1
fi

temp_dir=$(mktemp -t -d -p ./)
cd $temp_dir


input_video=$1
output_video=$2
video_bitrate=$3
audio_bitrate=$4
ffmpeg=$5
ffprobe=$6

echo $(pwd)
# < /dev/null prevents ffmpeg from reading standard input
$ffmpeg -i "$input_video" -loglevel error -hide_banner -codec:v libx264 -profile:v high -preset veryslow -movflags faststart -b:v $video_bitrate -minrate 400000 -threads 0 -pass 1 -an -f mp4 -y /dev/null < /dev/null
$ffmpeg -i "$input_video" -loglevel error -hide_banner -strict -2 -c:v libx264 -preset veryslow -movflags faststart -b:v $video_bitrate -minrate 400000 -threads 0 -pass 2 -c:a aac -b:a $audio_bitrate -y "$output_video" < /dev/null

cd ../
rm -rf $temp_dir
