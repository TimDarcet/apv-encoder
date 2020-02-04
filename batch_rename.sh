#! /bin/bash

# Rename all .mp4 files in $1 (max depth 3) to the format for the encoding script
# $1 : folder to rename
# $2 : bitrate coef to give

for i in $(find "$1" -maxdepth 3 -type f -name "*.mp4" | sort )
do
mv "$i" "${i%.*}_$2.${i##*.}"
done
