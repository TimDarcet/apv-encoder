# Encodage de l'APV

Plus d'infos -> https://wikix.polytechnique.org/index.php?title=APV/Dossier_de_passation/Encodage

## Principe

Le but de script est d'encoder (i.e de changer la taille et le format de fichier des vidéos)
Ce script encode les vidéos placées dans le 
les vidéos plac
```bash
Usage: encode.py [OPTIONS]

  Encodes the folder down to the target size
  Distributes the calculation to computers through ssh
  In order to be encoded using a coefficient, files
  should be placed in folders containing a file named '.coef' and
  containing a single integer.

Options:
  -f, --folder-to-encode DIRECTORY
                                  Path to folder to be encoded using ffmpeg
                                  [required]
  -s, --target-size INTEGER       Target size of the encoded folder, in MB
                                  [required]
  -c, --computers-file FILENAME   A file containing the ssh connection
                                  addresses of the other computers to
                                  distribute on
  -m, --ffmpeg-path TEXT          FFMPEG path. Default : ${whereis ffmpeg}
  -p, --ffprobe-path TEXT         FFPROBE path. Default : ${whereis ffprobe}
  -t, --max-threads INTEGER       Maximum simultaneous threads on a single
                                  computer (useful if low number of
                                  computers). 0 disables the limit. Default :
                                  0
  --help                          Show this message and exit.
```
