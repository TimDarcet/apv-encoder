#!/bin/bash
 if [ -z $1 -o -z $2 ]; then
     exit 1
 fi
 
 #encoding script
 #give it a folder to encode and a target size in megabytes and it does the rest

 #files should be named according to pattern <name>_<coef>.<extension>, where coef is an arbitrary coefficient measuring the quality of the encoded video.
 #e.g.: if one file has a coef of 1 and the other a coef of 2, the second will have a bitrate twice higher
 #the default coef is 6 (and that's absolutely arbitrary)

 #The second step (two-pass encoding) is distributed
 #There should exist a file at ~/computers_name that contains all of the logins to the salles infos computers (e.g.: jtx@dordogne.polytechnique.fr)
 #There should be at least as many computers as files in the APV, as there is one file distributed to each computer, and I didn't implement anything to distribute anything when there are no computers left. There are about 200 computers. And fuck the respo encodage of the year the APV will have more than 200 videos, I guess.

 #Creates a temp directory from which it makes the encoding
 #Necessary for different processes not to overlap
 ffmpeg=~/ffmpeg-static/ffmpeg
 ffprobe=~/ffmpeg-static/ffprobe
 
 temp_dir=$(mktemp -t -d -p ./)
 cd $temp_dir

 #Parameters
 folder_to_encode="../"$1
 desired_size=$(echo "$2*10^6" | tr -d $'\r' | bc)
 video_quality_factor="28"
 audio_bitrate=$(echo "192*10^3" | bc)

 #Deals with complex file names
 SAVEIFS=$IFS
 IFS=$(echo -en "\n\b")

 #The first loop : encodes with constant quality
 mkdir "$folder_to_encode/../constant_quality_output"
 cp ~/computers_name ./computers_name.tmp
 total_size=0
 total_size_coeffed=0
 total_coef=0
 mkdir ../locks
 for video in $(find "$folder_to_encode" -maxdepth 3 -type f -name "*.mp4" | sort )
 do
     foldername=$(basename $(dirname $(dirname $video)))/$(basename $(dirname $video))
     mkdir -p "$folder_to_encode/../constant_quality_output/$foldername"
     filename=$(basename $video)
     computer=$(head -n1 ./computers_name.tmp)
     ssh -oStrictHostKeyChecking=no $computer "cd $(dirname $(pwd)) && touch ./locks/$computer && $ffmpeg -i $(dirname $(pwd))/${video#../} -c:v libx264 -preset medium -crf $video_quality_factor -pix_fmt yuv420p -threads 0 -c:a copy -y ${folder_to_encode#../}/../constant_quality_output/$foldername/$filename > ./locks/$computer && rm -f ./locks/$computer" &
     printf "[%s] encodage n°1 de %s lancé sur %s.\n" $(date +%H:%M:%S) $video $computer
     sed -i '1d' ./computers_name.tmp
 done 
 rm ./computers_name.tmp
 sleep 5
 printf "========================================
 [%s] encodages n°1 (qualité constante) de %s lancés.
 ========================================\n" $(date +%H:%M:%S) $folder_to_encode
 
 while [ "$(ls -A ../locks)" ]
 do
    sleep 7
    printf "[%s] %d videos encore en traitement. Attente" $(date +%H:%M:%S) $(ls ../locks | wc -l)
    sleep 1
    printf "."
    sleep 1
    printf "."
    sleep 1
    printf "."
    sleep 1
    printf "\n"
 done

#calculate the total size 
 for video in $(find "$folder_to_encode" -maxdepth 3 -type f -name "*.mp4" | sort )
 do
     foldername=$(basename $(dirname $(dirname $video)))/$(basename $(dirname $video))
     filename=$(basename $video)
     # Read coef
     tmp=${filename%.*}
     coef=${tmp##*_}
     re='^[0-9]+$'
     if [[ $coef =~ $re ]]
     then
        total_coef=$(($total_coef+$coef))   
     else
        coef=6
        total_coef=$(($total_coef+6))
     fi
     size=$($ffprobe -v error -show_entries format=size -of default=noprint_wrappers=1:nokey=1 "$folder_to_encode/../constant_quality_output/$foldername/$filename")
     total_size=$(($total_size + $size))
     total_size_coeffed=$(($total_size_coeffed + $coef * $size))
 done

 printf "========================================
[%s] encodages n°1 (qualité constante) de %s terminés.
========================================\n" $(date +%H:%M:%S) $folder_to_encode 
 

 #The second loop : encodes the whole to respect size limit
 #See https://trac.ffmpeg.org/wiki/Encode/H.264 for more info on two-pass encoding
 mkdir "$folder_to_encode/../encoding_final_output"
 cp ~/computers_name ./computers_name.tmp
 for video in $(find "$folder_to_encode" -maxdepth 3 -type f -name "*.mp4" | sort )
 do
     foldername=$(basename $(dirname $(dirname $video)))/$(basename $(dirname $video))
     mkdir -p "$folder_to_encode/../encoding_final_output/$foldername"
     filename=$(basename "$video")
     if [ -f "$folder_to_encode/../constant_quality_output/$foldername/$filename" ]; then
         #read coef
         tmp=${filename%.*}
         coef=${tmp##*_}
         re='^[0-9]+$'
         if [[ $coef =~ $re ]]
         then
             coef=$coef   
         else
             coef=6
         fi
         #calculate bitrate
         constant_quality_bitrate=$($ffprobe -v error -show_entries format=bit_rate -of default=noprint_wrappers=1:nokey=1 "$folder_to_encode/../constant_quality_output/$foldername/$filename")
         video_bitrate=$(echo "($desired_size*$constant_quality_bitrate*$coef)/$total_size_coeffed-$audio_bitrate" | bc )
         #two-pass encode
         ssh -oStrictHostKeyChecking=no $(head -n1 ./computers_name.tmp) "$(dirname $(pwd))/two_pass_one_file.sh $(dirname $(pwd))/${video#../} $(dirname $(pwd))/${folder_to_encode#../}/../encoding_final_output/$foldername/$filename $video_bitrate $audio_bitrate" &
         #../two_pass_one_file.sh "$video" "$folder_to_encode/../encoding_final_output/$foldername/$filename" $video_bitrate $audio_bitrate
         sed -i '1d' ./computers_name.tmp
         #$ffmpeg -i "$video" -codec:v libx264 -profile:v high -preset veryslow -b:v $video_bitrate -threads 0 -pass 1 -an -f mp4 -y /dev/null
         #$ffmpeg -i "$video" -strict -2 -c:v libx264 -preset veryslow -b:v $video_bitrate -threads 0 -pass 2 -c:a aac -b:a $audio_bitrate -y "$folder_to_encode/../encoding_final_output/$foldername/$filename"
         printf "[%s] encodage n°2 de %s effectué.\n" $(date +%H:%M:%S) $video
     else
         echo $(printf "Erreur : fichier %s non trouve dans le dossier %s/constant_quality_output !" "$filename" "$folder_to_encode")
     fi
 done 
 
 printf "========================================
 [%s] encodage n°2 (final) de %s effectué.
 ========================================\n" $(date +%H:%M:%S) $folder_to_encode
 
 #Delete temporary files
 rm -rf "$folder_to_encode/../constant_quality_output"
 cd ../
 rm -rf $temp_dir 

 #Restores filename dealing configuration
 IFS=$SAVEIFS
