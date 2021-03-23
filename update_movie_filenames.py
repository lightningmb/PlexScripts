#!/usr/bin/env python3

import os
import glob
import argparse
import re
import requests
import imdb
import enzyme
import pdb
from io import BytesIO
import PIL.ImageTk
import PIL.Image
import tkinter

imdb_interface = imdb.IMDb()

TRACE = False

UPDATE_ID = False

IMDB_KINDS = [
    "tv series", 
    "movie", 
    "episode", 
    "video movie", 
    "tv movie", 
    "short", 
    "video game", 
    "tv miniseries"
]
              
EXTRAS_DIRS = [
    "Deleted Scenes",
    "Featurettes",
    "Interviews",
    "Scenes",
    "Shorts",
    "Trailers",
    "Other"
]


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", help="Directory to update", default=os.getcwd())
    parser.add_argument("-t", "--trace", help="Trace into script on failure", action="store_true", default=False)
    parser.add_argument("-a", "--all", help="Update all files even if they are properly named, excluding MANUALLY_NAMED", action="store_true", default=False)
    parser.add_argument("-k", "--kind", help="The kind of media", default="movie", choices=IMDB_KINDS)
    parser.add_argument("-u", "--update-id", help="Update IMDB IDs if already present", action="store_true", default=False)
    return parser.parse_args()


def get_list_of_movies(movies_dir):
    return [x for x in os.listdir(movies_dir) if os.path.isdir(os.path.join(movies_dir, x)) and os.listdir(os.path.join(movies_dir, x))]
    
    
def prompt_for_imdb_number(movie_title):
    return input("Enter IMDB Number for {}: ".format(movie_title))
    

def prompt_for_year(movie_title):
    return input("Enter year for {}: ".format(movie_title))
    
def normalize_title(title):
    return re.sub("[^a-zA-Z0-9]", "", title).lower()
    
def button_set_and_exit(root, index):
        root.choice = index
        root.quit()    
    
def choice_of_titles(options):
    root = tkinter.Tk()
    root.choice = -1
    covers = []
    photos = []
    functions = []
    frame = tkinter.Frame(root)
    for index, title in enumerate(options):
        frame.rowconfigure(int(index / 5) + 1, weight=1)
        url = title.get_fullsizeURL()
        label_text = "{}) {} ({}) ID: {}".format(index, title.data["title"], title.data["year"] if "year" in title.data.keys() else "", title.movieID)
        callback = lambda i=index: button_set_and_exit(root, i)
        try:
            response = requests.get(url, stream=True)
        except:
            button = tkinter.Button(frame, text=label_text, command=callback)
            button.grid(row=int(index / 5) + 1, column=int(index % 5) + 1)
        else:
            if response.status_code == 200:
                photos.append(PIL.Image.open(BytesIO(response.content)))
                photos[-1].thumbnail((250,250))
                covers.append(PIL.ImageTk.PhotoImage(photos[-1]))
                button = tkinter.Button(frame, text=label_text, image=covers[-1], command=callback, compound="bottom")
                button.grid(row=int(index / 5) + 1, column=int(index % 5) + 1)
            else:
                button = tkinter.Button(frame, text=label_text, command=callback)
                button.grid(row=int(index / 5) + 1, column=int(index % 5) + 1)
    manual_callback = lambda i=-1: button_set_and_exit(root, i)
    manual = tkinter.Button(frame, text="-1) None of these", command=manual_callback)
    manual.grid(row=int(len(options) / 5) + 1, column=(len(options) % 5) + 1)
    frame.pack()
    tkinter.mainloop()
    choice = root.choice
    root.destroy()
    return choice


def create_file_name_prefix(movie_title, kind="movie", files=[]):
    filename = [movie_title]
    imdb_id = None
    year = None
    if not UPDATE_ID:
        ids = list(set(re.findall("imdb-t?t?\d+", "".join(files))))
        if len(ids) == 1:
            imdb_id = re.findall("\d+", ids[0])[0]
            year = list(set(re.findall("\((\d\d\d\d)\)", "".join(files))))[0]
            return "{} ({}) {{imdb-tt{}}}".format(movie_title, year, imdb_id), imdb_id
    if movie_title.lower().endswith("bonus_disc"):
        return movie_title, 0
    search_results = imdb_interface.search_movie(movie_title)
    normalized_title = normalize_title(movie_title)
    exact_matches = [x for x in search_results if kind in x.data["kind"] and normalize_title(x.data["title"]) == normalized_title]
    possible_matches = [x for x in search_results if kind in x.data["kind"] and normalize_title(x.data["title"]).startswith(normalized_title)]
    if len(exact_matches) == 1:
        print("Found IMDB Match for {}".format(movie_title))
        imdb_id = exact_matches[0].movieID
        year = exact_matches[0].data["year"] if "year" in exact_matches[0].data.keys() else None
    elif len(exact_matches) > 1:
        print("Found mulitple matches for {} please select the correct one".format(movie_title))
        correct_index = choice_of_titles(exact_matches)
        if correct_index < 0:
            print("Please enter information manually...")
            imdb_id = prompt_for_imdb_number(movie_title)
            year = prompt_for_year(movie_title)
        else:
            imdb_id = exact_matches[correct_index].movieID
            year = exact_matches[correct_index].data["year"] if "year" in exact_matches[correct_index].data.keys() else None
    elif len(possible_matches) > 1:
        print("Found mulitple matches for {} please select the correct one".format(movie_title))
        correct_index = choice_of_titles(possible_matches)
        if correct_index < 0:
            print("Please enter information manually...")
            imdb_id = prompt_for_imdb_number(movie_title)
            year = prompt_for_year(movie_title)
        else:
            imdb_id = possible_matches[correct_index].movieID
            year = possible_matches[correct_index].data["year"] if "year" in possible_matches[correct_index].data.keys() else None
    elif len(possible_matches) == 1:
        print("Found IMDB Match for {}".format(movie_title))
        imdb_id = possible_matches[0].movieID
        year = possible_matches[0].data["year"] if "year" in possible_matches[0].data.keys() else None
    elif len(search_results) > 0:
        print("Search returned results, but could not find the right one")
        correct_index = choice_of_titles(search_results)
        if correct_index < 0:
            print("Please enter information manually...")
            imdb_id = prompt_for_imdb_number(movie_title)
            year = prompt_for_year(movie_title)
        else:
            imdb_id = search_results[correct_index].movieID
            year = search_results[correct_index].data["year"] if "year" in search_results[correct_index].data.keys() else None
    else:
        print("Could not find a match in IMDB, please enter information manually...")
        if TRACE:
            pdb.set_trace()
        imdb_id = prompt_for_imdb_number(movie_title)
        year = prompt_for_year(movie_title)
    if year:
        filename.append("({})".format(year))
    if imdb_id:
        filename.append("{{imdb-tt{}}}".format(imdb_id))
    return " ".join(filename), imdb_id
    
    
def get_file_part_name(filename):
    return re.findall("(?:(?:_t)|(?:pt))(\d+)", filename)

def get_imdb_runtime(imdb_id):
    if not imdb_id:
        return 0
    try:
        imdb_movie = imdb_interface.get_movie(imdb_id)
    except:
        return 0
    else:
        imdb_interface.update(imdb_movie, ["main"]) 
        if "runtimes" in imdb_movie.data.keys() and imdb_movie.data["runtimes"]:
            return imdb_movie.data["runtimes"][0]
        else:
            return 0


def rename_files(movie_dir, kind="movie"):
    print("Renaming files in: {}".format(movie_dir))
    files = [x for x in os.listdir(movie_dir) if os.path.isfile(os.path.join(movie_dir, x)) and x != "MANUALLY_NAMED"]
    prefix, imdb_id = create_file_name_prefix(os.path.basename(movie_dir), kind, files)
    runtime = int(get_imdb_runtime(imdb_id))
    main_file_found = 0
    for old_file in files:
        old_name, extension = os.path.splitext(old_file)
        new_name = prefix
        if extension == ".mkv":
            if len(files) == 1:
                new_name += " - Main file"
            with open(os.path.join(movie_dir, old_file), "rb") as fi:
                try:
                    movie = enzyme.MKV(fi)
                except:
                    movie = None
            if movie and runtime and round(movie.info.duration.seconds / 60) == runtime:
                if not main_file_found:
                    new_name += " - Main file"
                else:
                    new_name += " - Main file ({})".format(main_file_found)
                main_file_found += 1
            
        part = get_file_part_name(old_name)
        if part:
            new_name += " - pt{}".format(part[-1])
        new_name += extension
        if old_file != new_name:
            os.rename(os.path.join(movie_dir, old_file), os.path.join(movie_dir, new_name))
        

def movie_files_compliant(movie_dir):
    movie_name = os.path.basename(movie_dir)
    return all([
        (movie_name in x and ("imdb" in x or "bonus_disc" in movie_name.lower())) for x in os.listdir(movie_dir) if os.path.isfile(os.path.join(movie_dir, x))
    ])
        

def create_extras_directories(movie_dir):
    missing = [x for x in EXTRAS_DIRS if not os.path.isdir(os.path.join(movie_dir, x)) and not os.path.exists(os.path.join(movie_dir, x))]
    if missing:
        print("Creating missing extras directories in {}".format(movie_dir))
        for directory in missing:
            os.mkdir(os.path.join(movie_dir, directory))
    
def main(args):
    global TRACE
    global UPDATE_ID
    movies_dir = os.path.abspath(args.directory)
    TRACE = args.trace
    UPDATE_ID = args.update_id
    print("Scanning movies in {}".format(movies_dir))
    movies = [x for x in os.listdir(movies_dir) if os.path.isdir(os.path.join(movies_dir, x))]
    for movie_title in movies:
        movie_dir = os.path.join(movies_dir, movie_title)
        if (not movie_files_compliant(movie_dir) or args.all) and "MANUALLY_NAMED" not in os.listdir(movie_dir):
            try:
                rename_files(movie_dir, args.kind)
            except:
                if TRACE:
                    pdb.set_trace()
                else:
                    raise
        else:
            print("\t{} is already named properly".format(movie_title))
        create_extras_directories(movie_dir)
    
if __name__ == "__main__":
    main(get_args())