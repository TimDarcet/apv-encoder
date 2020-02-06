#!/bin/bash
if [ -z $1 -o -z $4 ]; then
    exit 1
fi

temp_dir=$(mktemp -t -d -p ./)
cd $temp_dir


ffmpeg=~/ffmpeg-static/ffmpeg
ffprobe=~/ffmpeg-static/ffprobe

input_video=$1
output_video=$2
video_bitrate=$3
audio_bitrate=$4

echo $(pwd)
# < /dev/null prevents ffmpeg from reading standard input
$ffmpeg -i "$input_video" -codec:v libx264 -profile:v high -preset veryslow -b:v $video_bitrate -minrate 400000 -threads 0 -pass 1 -an -f mp4 -y /dev/null < /dev/null
$ffmpeg -i "$input_video" -strict -2 -c:v libx264 -preset veryslow -b:v $video_bitrate -minrate 400000 -threads 0 -pass 2 -c:a aac -b:a $audio_bitrate -y "$output_video" < /dev/null

cd ../
rm -rf $temp_dir 

