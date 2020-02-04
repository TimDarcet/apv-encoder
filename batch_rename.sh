#! /bin/bash

# Rename all files in $1/* to the format for the encoding script
# $1 : folder to rename
# $2 : bitrate coef to give

for i in $1/*/*
do
mv "$i" "${i%.*}_$2.${i##*.}"
done
