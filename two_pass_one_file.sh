#!/bin/bash
if [ -z $1 -o -z $4 ]; then
    exit 1
fi

ffmpeg="~/ffmpeg-static/ffmpeg"
ffprobe="~/ffmpeg-static/ffprobe"

input_video=$1
output_video=$2
video_bitrate=$3
audio_bitrate=$4

echo $(pwd)
$ffmpeg -i "$input_video" -codec:v libx264 -profile:v high -preset veryslow -b:v $video_bitrate -threads 0 -pass 1 -an -f mp4 -y /dev/null
$ffmpeg -i "$input_video" -strict -2 -c:v libx264 -preset veryslow -b:v $video_bitrate -threads 0 -pass 2 -c:a aac -b:a $audio_bitrate -y "$output_video"
