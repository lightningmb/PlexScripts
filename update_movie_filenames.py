#!/usr/bin/env python3

import os
import functools
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

ASPECT_RATIO_MAP = {
    (4, 3): "Fullscreen",
    (16, 9): "Widescreen",
    # Non-standard ratios below
    (853, 480): "Widescreen",
    (109, 60): "Widescreen",
    (109, 80): "Fullscreen",
    (3, 2): "Fullscreen"
}


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", help="Directory to update", default=os.getcwd())
    parser.add_argument("-t", "--trace", help="Trace into script on failure", action="store_true", default=False)
    parser.add_argument("-a", "--all",
                        help="Update all files even if they are properly named, excluding MANUALLY_NAMED",
                        action="store_true", default=False)
    parser.add_argument("-k", "--kind", help="The kind of media", default="movie", choices=IMDB_KINDS)
    parser.add_argument("-u", "--update-id", help="Update IMDB IDs if already present", action="store_true",
                        default=False)
    parser.add_argument("-p", "--print-manual", help="Prints out folders missing the main files", action="store_true",
                        default=False)
    return parser.parse_args()


def get_list_of_movies(movies_dir):
    return [x for x in os.listdir(movies_dir) if
            os.path.isdir(os.path.join(movies_dir, x)) and os.listdir(os.path.join(movies_dir, x))]


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
        label_text = "{}) {} ({}) ID: {}".format(index, title.data["title"],
                                                 title.data["year"] if "year" in title.data.keys() else "",
                                                 title.movieID)
        callback = lambda i=index: button_set_and_exit(root, i)
        try:
            response = requests.get(url, stream=True)
        except:
            button = tkinter.Button(frame, text=label_text, command=callback)
            button.grid(row=int(index / 5) + 1, column=int(index % 5) + 1)
        else:
            if response.status_code == 200:
                photos.append(PIL.Image.open(BytesIO(response.content)))
                photos[-1].thumbnail((250, 250))
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
    exact_matches = [x for x in search_results if
                     kind in x.data["kind"] and normalize_title(x.data["title"]) == normalized_title]
    possible_matches = [x for x in search_results if
                        kind in x.data["kind"] and normalize_title(x.data["title"]).startswith(normalized_title)]
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
            year = exact_matches[correct_index].data["year"] if "year" in exact_matches[
                correct_index].data.keys() else None
    elif len(possible_matches) > 1:
        print("Found mulitple matches for {} please select the correct one".format(movie_title))
        correct_index = choice_of_titles(possible_matches)
        if correct_index < 0:
            print("Please enter information manually...")
            imdb_id = prompt_for_imdb_number(movie_title)
            year = prompt_for_year(movie_title)
        else:
            imdb_id = possible_matches[correct_index].movieID
            year = possible_matches[correct_index].data["year"] if "year" in possible_matches[
                correct_index].data.keys() else None
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
            year = search_results[correct_index].data["year"] if "year" in search_results[
                correct_index].data.keys() else None
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


def logical_sort(A, B):
    if len(A) > len(B):
        return 1
    elif len(A) < len(B):
        return -1
    else:
        if A > B:
            return 1
        elif A < B:
            return -1
        else:
            return 0


def get_gcd(a, b):
    "Return greatest common divisor for a and b."
    while a:
        a, b = b % a, a
    return b


def aspect_ratio_as_ints(width, height):
    "Return an integer ratio tuple like (16, 9)."
    gcd = get_gcd(width, height)
    return int(width / gcd), int(height / gcd)


def get_aspect_ratio(movie, filename):
    if movie:
        width = movie.video_tracks[0].display_width
        height = movie.video_tracks[0].display_height
        ratio_tuple = aspect_ratio_as_ints(width, height)
        if ratio_tuple in ASPECT_RATIO_MAP:
            return ASPECT_RATIO_MAP[ratio_tuple]
        else:
            print("\t{} has an unknown aspect ratio - {}".format(filename, ratio_tuple))
    return None


def rename_files(movie_dir, kind="movie"):
    print("Renaming files in: {}".format(movie_dir))
    files = sorted(
        [x for x in os.listdir(movie_dir) if os.path.isfile(os.path.join(movie_dir, x)) and x != "MANUALLY_NAMED"],
        key=functools.cmp_to_key(logical_sort))
    prefix, imdb_id = create_file_name_prefix(os.path.basename(movie_dir), kind, files)
    runtime = int(get_imdb_runtime(imdb_id))
    main_file_found = 0
    filename_maps = []
    for old_file in files:
        old_name, extension = os.path.splitext(old_file)
        new_name = prefix
        is_main_file = False
        movie = None
        if extension == ".mkv":
            if len(files) == 1:
                new_name += " - Main file"
            else:
                with open(os.path.join(movie_dir, old_file), "rb") as fi:
                    try:
                        movie = enzyme.MKV(fi)
                    except:
                        movie = None
                if movie and (movie.info.duration.seconds - (movie.info.duration.seconds % 60)) / 60 in [runtime - 1,
                                                                                                         runtime,
                                                                                                         runtime + 1]:
                    if not main_file_found:
                        new_name += " - Main file"
                    else:
                        new_name += " - Main file ({})".format(main_file_found)
                    print("\tFound main file")
                    main_file_found += 1
                    is_main_file = True
        part = get_file_part_name(old_name)
        if part and not is_main_file:
            new_name += " - pt{}".format(part[-1])
        new_name += extension
        filename_maps.append((old_file, new_name, is_main_file, get_aspect_ratio(movie, new_name)))
    aspect_ratios_found = list(set([x[3] for x in filename_maps if x[2]]))
    for name_map in filename_maps:
        old_file = name_map[0]
        new_name = name_map[1]
        is_main_file = name_map[2]
        if is_main_file and main_file_found == 2 and len(aspect_ratios_found) == 2:
            name, extension = os.path.splitext(new_name)
            new_name = name.replace(" (1)", "") + " - " + name_map[3] + extension
        if not is_main_file and main_file_found:
            if not os.path.isdir(os.path.join(movie_dir, "Other")):
                os.mkdir(os.path.join(movie_dir, "Other"))
            os.rename(os.path.join(movie_dir, old_file), os.path.join(movie_dir, "Other", new_name))
        elif old_file != new_name:
            try:
                os.rename(os.path.join(movie_dir, old_file), os.path.join(movie_dir, new_name))
            except:
                pdb.set_trace()


def movie_files_compliant(movie_dir):
    movie_name = os.path.basename(movie_dir)
    return all([
        (movie_name in x and ("imdb" in x or "bonus_disc" in movie_name.lower())) for x in os.listdir(movie_dir) if
        os.path.isfile(os.path.join(movie_dir, x))
    ])


def create_extras_directories(movie_dir):
    missing = [x for x in EXTRAS_DIRS if
               not os.path.isdir(os.path.join(movie_dir, x)) and not os.path.exists(os.path.join(movie_dir, x))]
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
    if args.print_manual:
        needs_manual_review = []
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
        if args.print_manual:
            main_files_list = [x for x in os.listdir(movie_dir) if "Main file" in x]
            if len(main_files_list) != 1:
                if len(main_files_list) == 2:
                    names = "".join(main_files_list)
                    if " - Fullscreen" not in names or " - Widescreen" not in names:
                        needs_manual_review.append((movie_title, "Multiple main files"))
                else:
                    reason = "Missing main file" if len(main_files_list) == 0 else "Multiple main files"
                    needs_manual_review.append((movie_title, reason))
        create_extras_directories(movie_dir)
    print("{} Movie directories processed".format(len(movies)))
    if args.print_manual:
        if needs_manual_review:
            print("The following directories need manual review:\n")
            filename_format_str = "{{0:<{}}}{{1}}".format(
                max([len(os.path.join(movies_dir, x[0])) for x in needs_manual_review]) + 4)
            print("\n".join(
                [filename_format_str.format(os.path.join(movies_dir, x[0]), x[1]) for x in needs_manual_review]))
        else:
            print("All directories properly organized")


if __name__ == "__main__":
    main(get_args())