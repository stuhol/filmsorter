import os
from glob import glob

def glob_dirs():
    for dir in glob("/volume1/Media/Films/*"):
        print dir

def walk_dirs():
    for root, dirs, files in os.walk("/volume1/Media/Films"):
        if len(dirs) != 0:
            if dirs != ["@eaDir"]: 
                if "@eaDir" not in root:
                   #print dirs
                    print root

walk_dirs()
