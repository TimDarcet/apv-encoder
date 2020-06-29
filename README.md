# Encodage de l'APV

Plus d'infos -> https://wikix.polytechnique.org/index.php?title=APV/Dossier_de_passation/Encodage

## Principe

Le but de script est d'encoder (i.e de changer la taille et le format de fichier des vidéos) les vidéos placées dans le dossier `folder-to-encode` ainsi que dans les sous-dossiers de ce dossier, de telle sorte que la taille mémoire finale de toutes les vidéos encodées corresponde à `target-size`. Ce script crée un dossier `encoding_final_output` dans lequel il créera les vidéos encodées en respectant la structure de dossier de `folder-to-encode`.
Ce script permet de distribuer l'encodage des vidéos sur les machines de la salle info. (voir la section du readme correspondante)

## Coefficients de qualité

Finalement, on peut choisir en fonction des sous-dossiers de `folder-to-encode` quelle sera la qualité (c'est à dire le bitrate) relative de l'encodage de ce sous dossier par rapport à un autre sous-dossier. Cela est fait au travers de coefficient. Par exemple, une vidéo qui a un coefficient de 8 aura un bitrate (et donc une qualité) deux fois supérieure à une vidéo ayant un coefficient de 4. Cela permet par exemple de réduire la taille finale de certaines vidéos au profit d'autres vidéos qui ont besoin d'un meilleur bitrate.

Comment définir les coefficients? Il suffit de placer un fichier appelé `.coef`, a l'intérieur de l'arborescence de `folder_to_encode`, dont le contenu est un entier, correspondant au coefficient. Une vidéo possède alors le coefficient du premier fichier `.coef` lorsque l'on remonte la hiérarchie des fichiers.
Exemple:
- **Folder to encode**
  - `.coef` avec le coef **4**
  - les vidéo ici ont un coef **4**
  - **Sous-dossier** *(sans fichier `.coef`)*
    - les vidéo ici ont un coef **4**
    - **Sous-sous-dossier** *(sans fichier `.coef`)*
      - les vidéo ici ont un coef **4**
    - **Sous-sous-dossier**
      - `.coef` avec le coef **7**
      - les vidéo ici ont un coef **7**
  - **Sous-dossier**
    - `.coef` avec le coef **2**
    - les vidéo ici ont un coef **2**
    - **Sous-sous-dossier** *(sans fichier `.coef`)*
      - les vidéo ici ont un coef **2**

Si vous avez toujours des doutes sur la manière d'affecter des coeffs, voici le code qui permet de déterminer le coefficient d'une vidéo (on part de la vidéo, et on remonte la structure de fichier jusqu'à trouver un fichier `.coef`):
```python
def getVideoCoeff(video):
    coefpath = video.parent / '.coef'
    i = 0
    while not coefpath.is_file():
        coefpath = coefpath.parent.parent / '.coef'
        i += 1
        if i > 100:
            raise FileNotFoundError
    return int(coefpath.read_text().strip())
```

Il doit donc y avoir **necessairement** un fichier `.coef` à la racine du dossier `folder_to_encode`, sinon certaines vidéos risquent de ne pas avoir de coefficient.

## Execution en local sur un seul ordinateur

Installer au préalable ffmpeg et ffprobe, ou se munir des binaries.
L'encodeur execute le traitement des vidéos en se connctant à la machine par ssh. Bien que cela soit rigoureusement inutile sur un seul ordinateur, cela est fait et penser pour pouvoir distribuer l'execution sur plusieurs machines.
Afin de faire tourner l'encodeur sur un seul ordinateur, il faut ouvrir un serveur ssh en local, et vérifier que `ssh localhost` permet de se connecter au shell sans mettre de mot de passe (utiliser une clé rsa).
Créer un fichier contenant simplement:
```
localhost
```
et ensuite il suffira de passer le nom de ce fichier à l'argument `--computers-file`. Attention, si vous laissez `--max-threads` à sa valeur par défaut (i.e 0), alors le programme ne va pas limiter le nombre de traitement de vidéos en parallèle sur l'ordinateur, ce qui risque de le faire planter. Il est recommandé de mettre `--max-thread` à 1,5 fois le nombre de coeurs physiques de la machine

## Execution sur les salles infos

On a besoin
- D'un home partagé, avec de la taille (donc utiliser le compte `jtx`).
- De pouvoir, tout en étant connecté à `jtx` sur une certaine machine de la salle info, se `ssh` sur une autre machine de la salle info, sur le compte `jtx`. (Donc il faut mettre la public key de `jtx` dans le `authorized_keys` de `jtx`)
- D'avoir déja réuni toutes les vidéos à encoder dans un dossier (qui sera le `folder_to_encode`) dans le HOME de `jtx`
- Des binaries de `ffmpeg` et `ffprobe` dans le HOME
- De la liste des noms DNS des ordis de la salle infos qui sont ups et dispos pour faire tourner les encodings, dans un fichier dont le nom sera donné à l'argument `--computers-file`. Il faut mettre un nom par ligne. Evitez de mettre l'ordi "master", depuis lequel vous lancez l'encodage, dans ce fichier.

## Utilisation du CLI

```bash
$ ./encode.py --help

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
