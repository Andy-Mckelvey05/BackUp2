from colorama import Fore
from datetime import date
from tqdm import tqdm
import threading
import py7zr
import time
import sys
import os

display_lock = threading.Lock()  # Sets up queue for console display, otherwise the console becomes a mess


# -------------------- Utility --------------------


# Mono-spaces tqdm bars description for better display
def format_bar_desc(name):
    max_length = 30  # Change this for personal preferences
    if len(name) >= max_length:
        return name[:max_length - 1] + "-"
    else:
        return name.ljust(max_length)  # ljust appends spaces


# Simplify code by wrapping this into a function, Creates TQDM Bar
def create_tqdm_bar(items=None, colour="WHITE", desc="Pending...", leave=True):
    if not items:
        items = []
    return tqdm(
        total=len(items),
        leave=leave,
        colour=colour,
        bar_format="{l_bar}{bar:50} | {n_fmt}/{total_fmt}",
        desc=desc,
    )


# Formats an inputted number of seconds into a h:m:s format
def format_time(time_input):
    s = round(time_input)
    m, s = divmod(s, 60)  # Get minutes and remaining seconds
    h, m = divmod(m, 60)  # Get hours and remaining minutes

    if h > 0:
        return f"{h}h:{m}m:{s}s"
    elif m > 0:
        return f"{m}m:{s}s"
    else:
        return f"{s}s"


# Prints text as a specific colour
def print_as_colour(string, colour, same_line=False):
    if same_line:
        print(colour + string + Fore.RESET, end="")
    else:
        print(colour + string + Fore.RESET)


# Prompts user for input, has consistent formatting
def get_user_input(string):
    print_as_colour(string, Fore.CYAN, True)
    return input(": ")


# Validates if an input can be a number, if so: convert and return
def try_parse_int(value):
    try:
        return int(value)
    except ValueError:
        return None


# Prints warning if there is an error, can also halt execution
def print_error(string, close=False):
    print_as_colour("[ERROR] - " + string, Fore.RED)
    if close:
        sys.exit(1)


# Gets the name of the new file
def get_archive_name(chosen_file):
    archive_name, _ = os.path.splitext(os.path.basename(chosen_file))
    archive_date = date.today().strftime("%d.%m.%y")
    return archive_name + ' - ' + archive_date


# Removes redundancy or invalid directory's from the archive list
def sanitise_paths(unsanitized_paths):
    if not unsanitized_paths:
        print_error("No directories to process. Exiting.", True)

    valid_paths = unsanitized_paths[:]  # Creates a copy of the array to remove from, avoiding iteration issues
    program_dir = os.getcwd()

    for path in unsanitized_paths:
        # Remove empty paths
        if not path:
            valid_paths.remove(path)
            continue

        # Check if the path is a valid directory
        if not os.path.isdir(path):
            valid_paths.remove(path)
            print_error(f"'{path}' is not a valid directory, removed from list.")
            continue

        # Check if the path is a duplicate
        if valid_paths.count(path) > 1:
            num_dupes = valid_paths.count(path)
            for dupe in range(1, num_dupes):
                valid_paths.remove(path)
            print_error(f"'{path}' is duplicated {num_dupes} times, removed all but 1 from list.")
            continue

        # Remove smaller paths embedded in larger ones
        for embed_path in unsanitized_paths:
            if embed_path != path and embed_path.startswith(path):
                if embed_path in valid_paths:
                    valid_paths.remove(embed_path)
                    print_error(f"'{embed_path}' is already being backed up with '{path}', removed from list.")

        # Check if the path includes the program's directory, its parents, or its children
        if path.startswith(program_dir) or program_dir.startswith(path):
            valid_paths.remove(path)
            print_error(f"'{path}' overlaps with the program directory, removed from list.")
            continue

    if valid_paths:
        return valid_paths
    else:
        print_error("No valid directories to process. Exiting.", True)


# -------------------------------------------------


# Creates a 7z file with the given directory
def copy_directory_path(directory, thread_bar):
    if os.path.isdir(directory):
        base_dir_name = os.path.basename(directory.strip(os.sep))
        file_list = list(os.walk(directory))

        with display_lock:  # adds thread info to tqdm bar
            thread_bar.set_description(f"{format_bar_desc(base_dir_name)}")
            thread_bar.total = len(file_list)
            thread_bar.refresh()

        archive_path = os.path.join(target_file_path, f"{base_dir_name}.7z")
        with py7zr.SevenZipFile(archive_path, 'a') as Zip_file:
            for current_path, _, filenames in file_list:
                # Defines filepath from target_file_path
                relative_path = os.path.join(base_dir_name, str(os.path.relpath(current_path, directory)))

                # File (Yellow) bars are unordered as they are small & disappear after completion
                file_bar_name = f"{format_bar_desc(os.path.basename(current_path))}"
                file_bar = create_tqdm_bar(filenames, "YELLOW", file_bar_name, False)

                for file in filenames:  # Goes through each file, Adding it to the archive
                    new_source_file_path = os.path.join(current_path, file)
                    new_target_file_path = os.path.join(relative_path, file)
                    Zip_file.write(str(new_source_file_path), new_target_file_path)
                    with display_lock:  # Update the progress bar upon each file update
                        file_bar.update(1)

                with display_lock:  # Update the progress bar upon each directory update
                    thread_bar.update(1)
    else:
        print_error(f"Invalid directory: {directory}", True)


# Activates each thread, and sets up the progress bars
def run_threads():
    # Process bars need to be set up in a specific order to display correctly.
    # Main (Green) bar is shown first
    main_bar = create_tqdm_bar(selected_paths, "GREEN", f"{format_bar_desc('Archiving')}")

    progress_bars = []  # then creates all the thread (Blue) bars
    for _ in selected_paths:
        progress = create_tqdm_bar(colour="CYAN")  # Other properties defined in thread
        progress_bars.append(progress)

    threads = []  # Starts each thread, copying each user input separately
    for i, path in enumerate(selected_paths):
        thread = threading.Thread(target=copy_directory_path, args=(path, progress_bars[i]))
        threads.append(thread)
        thread.start()

    for thread in threads:  # Once each thread concludes, update the display
        thread.join()
        with display_lock:
            main_bar.update(1)
            main_bar.refresh()

    with display_lock:  # Closes the bars upon completion
        main_bar.close()
        for progress in progress_bars:
            progress.close()


# Gets users pick of preset
def get_presets():
    presets_path = os.getcwd() + r"\Presets"
    items = os.listdir(presets_path)

    if ".gitkeep" in items:
        items.remove(".gitkeep")

    if len(items) > 0:
        print_as_colour("\nPlease Select A Preset To Continue:", Fore.YELLOW)

        options = {}
        for i, item in enumerate(items, start=1):
            options[i] = item
            print(f"\t{i} : {item}")

        user_input = get_user_input("Selection")
        input_value = try_parse_int(user_input)
        if input_value and input_value in options:

            chosen_file = options[input_value]
            chosen_file_path = os.path.join(presets_path, chosen_file)
            _, file_extension = os.path.splitext(chosen_file_path)

            if file_extension.lower() == ".txt":
                return chosen_file_path
            else:
                print_error("Preset Must Be Type Txt")
                return get_presets()  # Recurs if user input is invalid
        else:
            print_error("You Have Not Selected A Valid Option")
            return get_presets()  # Recurs if user input is invalid
    else:
        print_error("You Must Create A Preset To Continue", True)


if __name__ == "__main__":
    chosen_preset = get_presets()
    target_file_path = os.getcwd() + rf"\BackUps\{get_archive_name(chosen_preset)}"
    os.makedirs(target_file_path, exist_ok=True)  # Places directory in files

    with open(chosen_preset, 'r') as preset:
        selected_paths_unsanitized = preset.read().split('\n')
    selected_paths = sanitise_paths(selected_paths_unsanitized)

    print_as_colour("\nCreating Archive:", Fore.GREEN)
    start_time = time.time()
    run_threads()  # Creates a 7z back up of each file in preset

    print_as_colour(f"\nBack-Up Has Been Created At:\n'{target_file_path}'", Fore.CYAN)
    print_as_colour(f"Time Taken: {format_time(time.time() - start_time)}\n", Fore.YELLOW)

