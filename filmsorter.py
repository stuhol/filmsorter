import os
from datetime import date, timedelta
import logging
from argparse import ArgumentParser
import omdb
from glob import glob
import subprocess
import pipes
import math
import re
import fnmatch

# Script name
SCRIPT_NAME = "Film Sorter"
# Script description
SCRIPT_DESCRIPTION = "Sorts films based on their title into years and genre folders"
'''
Arguments:

'''

# Run script in batch mode? None indicates take option from command line
BATCH_MODE = None
# Rename film folders
RENAME_FILMS = True
# Film file extensions
FILM_EXTENSIONS_REGEX = "avi|divx|m2ts|m4v|mkv|mov|mp4|mpg|wmv"
# Illegal filename characters 
ILLEGAL_FILENAME_CHARS = ['\\','/',':','*','?','"','<','>','|']

SYMLINK_CMD = "ln -s %s %s"
# Failed lookups logfile
FAILED_LOOKUP_FILE = "failed_lookups.txt"
# Title mismatch logfile
TITLE_MISMATCH_FILE = "title_mismatch.txt"
# Media path
MEDIA_PATH = "/volume1/Media/"
# Films path
FILMS_PATH = MEDIA_PATH + "Films/"
# Title path
TITLES_PATH = FILMS_PATH + "Titles/"
# Genre path
GENRES_PATH = FILMS_PATH + "Genres/"
# Year path
YEARS_PATH = FILMS_PATH + "Years/"
# IMDB rating path
IMDB_RATINGS_PATH = FILMS_PATH + "IMDB Ratings/"
# Film information text filename
FILM_INFO_FILENAME = "info.txt"

def search_films(title, year=None):
    #res = omdb.title(title)
    if year:
        res = omdb.search_movie(title, year=year)
    else:
        res = omdb.search_movie(title)
    
    return res

def get_film_information(imdb_id):
    return omdb.imdbid(imdb_id)

def create_symlink(source, destination):
    #source = pipes.quote(source)
    #destination = pipes.quote(destination)
    logging.info("Running: ln -s %s %s" % (source, destination))
    subprocess.call(['ln', '-s', source, destination])

def rename_film(film_path, film_information):

    dir_list = os.listdir(film_path)

    film_title = film_information.title
    # TODO CHECK FOR ILLEGAL CHARS
    if any(i in film_title for i in ILLEGAL_FILENAME_CHARS):
        # Replace illegal chars with ' -'
        for illegal_char in ILLEGAL_FILENAME_CHARS:
            film_title = film_title.replace(illegal_char, ' -')

    print film_title
                
    film_files = [filename for filename in dir_list
                    if re.search(FILM_EXTENSIONS_REGEX, filename, re.IGNORECASE)]

    # TODO only rename one file for now
    if len(film_files) == 1:
        film_filename, film_ext = os.path.splitext(os.path.join(film_path, film_files[0]))
        os.rename(film_filename + film_ext, os.path.join(film_path, "%s (%s)%s" % (film_title, film_information.year, film_ext))) 

    #print "Rename to : " + TITLES_PATH + "%s (%s)" % (film_information.title, film_information.year)

    new_film_path = TITLES_PATH + "%s (%s)" % (film_title, film_information.year)

    # Rename folder
    try:
        os.rename(film_path, new_film_path)
    except OSError:
        logging.error("Unable to rename film: %s" % new_film_path)
        return False

    return new_film_path

def generate_symlinks(film_path, film_information):
    # Create Genre path
    logging.info("Creating symlinks for %s" % film_path)
    
    generate_genre_symlinks(film_path, film_information)

    generate_year_symlinks(film_path, film_information)

    generate_imdb_rating_symlink(film_path, film_information)

def generate_imdb_rating_symlink(film_path, film_information):
    logging.info("Creating IMDB symlinks")

    if film_information['imdb_rating'] == 'N/A':
        logging.warning("No IMDB rating for %s" % film_path)
        return

    imdb_rating = str(int(math.floor(float(film_information['imdb_rating']))))
    imdb_rating_path = IMDB_RATINGS_PATH + imdb_rating

    logging.info("Adding film to IMDB rating %s" % imdb_rating)

    if not os.path.isdir(imdb_rating_path):
        logging.info("New IMDB rating folder, creating folder %s", imdb_rating_path)
        os.makedirs(imdb_rating_path)

    create_symlink(film_path, imdb_rating_path)

def generate_year_symlinks(film_path, film_information):
    logging.info("Creating year symlinks")
    
    year = film_information['year'].strip()

    if re.match("^\d{4}$", year) == None:
        logging.error("Year not of form YYYY for %s" % film_path)
        return

    year_path = YEARS_PATH + year + "/"

    logging.info("Adding film to %s" % year.strip())

    if not os.path.isdir(year_path):
        logging.info("New year found, creating folder %s" % year_path)
        os.makedirs(year_path)

    create_symlink(film_path, year_path)

def generate_genre_symlinks(film_path, film_information):
    logging.info("Creating genre symlinks")
    
    if film_information['genre'] == 'N/A':
        logging.warning("No genre for %s" % film_path)
        return

    for genre in film_information['genre'].split(','):
        genre_path = GENRES_PATH + genre.strip() + "/"

        logging.info("Adding film to %s" % genre.strip())
        if not os.path.isdir(genre_path):
            logging.info("New genre found, creating folder %s" % genre_path)
            os.makedirs(genre_path)
            
        create_symlink(film_path, genre_path)
        #quit()

def generate_film_info_file(film_path, film_information):
    info_fp = open(film_path + "/" + FILM_INFO_FILENAME, 'w')

    info_fp.write("Title: %s\r\n" % film_information.title.encode("utf8"))
    info_fp.write("Year: %s\r\n" % film_information.year.encode("utf8"))
    info_fp.write("IMDM Rating: %s\r\n" % film_information.imdb_rating.encode("utf8"))
    info_fp.write("Runtime: %s\r\n" % film_information.runtime.encode("utf8"))
    info_fp.write("Director: %s\r\n" % film_information.director.encode("utf8"))
    info_fp.write("Actors: %s\r\n" % film_information.actors.encode("utf8"))
    info_fp.write("Language: %s\r\n" % film_information.language.encode("utf8"))
    info_fp.write("Country: %s\r\n" % film_information.country.encode("utf8"))
    info_fp.write("Released: %s\r\n" % film_information.released.encode("utf8"))
    info_fp.write("Plot: %s" % film_information.plot.encode("utf8"))

    info_fp.close()

def process_film(film_path, film_information):
    if RENAME_FILMS:
        new_film_path = rename_film(film_path, film_information)
        if new_film_path:
            film_path = new_film_path
        else:
            logging.error("Couldn't rename film, skipping")
            return
        
    generate_symlinks(film_path, film_information)
    generate_film_info_file(film_path, film_information)

def walk_path(path):

    # Open failed lookup file
    failed_lookups_fp = open(FAILED_LOOKUP_FILE, 'w')
    
    # Open title mismatch file
    title_mismatch_fp = open(TITLE_MISMATCH_FILE, 'w')

    # List of existing films
    existing_films = []

    # Get list of all existing folders, use year as it is always populated
    for root, dirs, files in os.walk(YEARS_PATH):
        for dir in dirs:
            existing_films.append(dir)

    subdirs = next(os.walk(path))[1]
    for dir in subdirs:

        logging.info("Processing path: %s" % path + dir)

        if dir in existing_films:
            logging.info("%s already exists in organisation folders, skipping", dir)
            continue

        # Get film title, strip out year inbetween brackets
        try:
            film_title = dir[:dir.index('(')].strip()
        except ValueError:
            film_title = dir.strip()

        logging.info("Film title: \"%s\"" % film_title)

        # Get film year, using regex
        year_re = re.search(".*?\((\d{4})\)", dir)
        if year_re is not None:
            film_year = year_re.group(1)
            logging.info("Film year: %s" % film_year)
        else:
            logging.info("Film year not found")
            film_year = None

        film_search_results = search_films(film_title, film_year)
       
        logging.info("Search returned %s results" % len(film_search_results))

        film_path =  path + dir

        if len(film_search_results) == 0:
            logging.error("Unable to find film %s in OMDB" % film_title)
            failed_lookups_fp.write(film_path + "\n")
            continue

        film = None

        if len(film_search_results) > 1:
            for item in film_search_results:
                if item.title == film_title and item.year == film_year or item.title == film_title and film_year is None:
                    film = item
                    break
        elif len(film_search_results) == 1:
            film = film_search_results[0]

        if film is None:
            if not BATCH_MODE:
                print "Multiple search results found..."
                for i in range(0, len(film_search_results)):
                    print "Search Result: %d" % i
                    print "Title: %s" % film_search_results[i].title
                    print "Year: %s" % film_search_results[i].year
                    print "IMDB ID: %s\n" % film_search_results[i].imdb_id
                response = None
                while response is None or response is not 's' or response.isdigit() is False:
                    response = raw_input("Choose search result to use (enter 's' to skip): ")
                    if response is 's':
                        logging.error("Skipped %s" % film_title)
                        failed_lookups_fp.write(film_path + "\n")
                        film = None
                        break
                    elif response.isdigit():
                        film = film_search_results[int(response)]
                        break
            else:
                logging.warning("Multiple search results found for %s, skipping" % film_title)
                failed_lookups_fp.write("%s - Multiple search results\n" % film_path)

        if film is None:
            logging.warning("Multiple search results found for %s, user skipped" % film_title)
            failed_lookups_fp.write("%s - Multiple search results\n" % film_path)
            continue

        film_information = get_film_information(film['imdb_id'])

        if film_information['title'].lower() == film_title.lower():
            process_film(film_path, film_information)
        else:
            logging.warning("Film title to IMDB title mismatch for %s" % film_title)
            title_mismatch_fp.write(film_path + "\n")
            if not BATCH_MODE:
            # TODO add batch mode automation
                print "Folder film title:\t %s" % film_title
                print "OMDB film title:\t %s" % film_information['title']
                response = raw_input("Continue making symlinks for mismatch title? [y/n]: ")
                if response is 'y':
                    process_film(film_path, film_information)
            
if __name__ == '__main__':

    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logFormat = logging.Formatter(fmt='%(asctime)s - %(levelname)s:%(message)s', datefmt='%d/%m/%Y %H:%M:%S')

    logFileHandler = logging.FileHandler("filmsorter.log", mode='w')
    logFileHandler.setFormatter(logFormat)
    logger.addHandler(logFileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormat)
    logger.addHandler(consoleHandler)

    logging.info("Running %s" % SCRIPT_NAME)

    # Parse arguments from command line

    arg_parser = ArgumentParser(description=SCRIPT_DESCRIPTION)

    # Arguments
    # Example: arg_parser.add_argument('--argument', metavar='A', default=30, help='Argument help')
    arg_parser.add_argument('--batch', action='store_true', help="Run in batch mode and don't ask questions") 
    args = arg_parser.parse_args()
    if BATCH_MODE == None:
        BATCH_MODE = args.batch

    # Walk titles
    walk_path(TITLES_PATH)

