import argparse
import os
import re
import datetime # Used for potential timestamping (though time module is used currently)
import fnmatch  # Used for wildcard filename filtering
import time     # Used for timestamp generation in output filenames

def process_directory_input(directory_path, include_extensions, ignore_patterns):
    """
    Duplicate-Line-Identifier:
    Walks through a directory, finds files matching include/ignore criteria,
    and concatenates their content into a single timestamped output file.

    Args:
        directory_path (str): The path to the directory to process.
        include_extensions (list): List of file extensions to include (e.g., ['.log', '.txt']).
                                   If None or empty, all files are considered before applying ignore patterns.
        ignore_patterns (list): List of filename patterns (using fnmatch syntax) to ignore.

    Returns:
        str: The path to the concatenated output file if successful and files were found,
             None otherwise.
    """
    files_to_process = []
    # Normalize extensions to ensure they start with a dot for consistent matching.
    normalized_extensions = None
    if include_extensions:
        normalized_extensions = [f".{ext.lstrip('.')}" for ext in include_extensions]

    print(f"Scanning directory: {directory_path}")
    print(f"Including extensions: {normalized_extensions or 'All'}")
    print(f"Ignoring patterns: {ignore_patterns or 'None'}")

    for root, _, filenames in os.walk(directory_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            _, file_ext = os.path.splitext(filename)

            # 1. Check if the file should be ignored based on filename patterns.
            should_ignore = False
            if ignore_patterns:
                for pattern in ignore_patterns:
                    if fnmatch.fnmatch(filename, pattern):
                        should_ignore = True
                        break # No need to check other ignore patterns for this file
            if should_ignore:
                continue

            # 2. Check if the file has an allowed extension (if extensions are specified).
            if normalized_extensions:
                if file_ext.lower() not in normalized_extensions:
                    continue

            # If the file passes both checks, add it to the list for processing.
            files_to_process.append(file_path)

    if not files_to_process:
        print("No files found matching the criteria in the specified directory.")
        return None

    # Create the output filename using the directory name and a timestamp.
    folder_name = os.path.basename(os.path.normpath(directory_path))
    timestamp = time.strftime('%Y%m%d%H%M%S')
    # Place the output file in the current working directory for simplicity.
    output_filename = f"{folder_name}_MERGED_{timestamp}.txt"
    output_filepath = os.path.join(os.getcwd(), output_filename)

    print(f"\nFound {len(files_to_process)} files to merge into '{output_filepath}':")
    # Concatenate the content of the selected files into the output file.
    try:
        with open(output_filepath, 'w', encoding='utf-8', errors='ignore') as f_out:
            for i, file_path in enumerate(files_to_process):
                print(f"  Merging ({i+1}/{len(files_to_process)}): {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                        # Add header/footer comments indicating the source file.
                        f_out.write(f"\n# --- Start of content from: {os.path.basename(file_path)} ---\n")
                        f_out.write(f_in.read())
                        f_out.write(f"\n# --- End of content from: {os.path.basename(file_path)} ---\n")
                except Exception as read_err:
                    print(f"  [Warning] Could not read file: {file_path}. Error: {read_err}")
                    # Write a placeholder comment in the output for the unreadable file.
                    f_out.write(f"\n# !!! Error reading file: {os.path.basename(file_path)} - {read_err} !!!\n")
        print(f"Successfully merged files into: {output_filepath}")
        return output_filepath
    except Exception as write_err:
        print(f"Error writing merged file '{output_filepath}': {write_err}")
        return None

def sanitize_file(input_file_path, output_file_path, patterns_to_remove_line, patterns_to_strip_prefix):
    """
    Reads an input file, processes lines based on regex patterns, and writes
    the potentially modified lines to an output file.

    - Lines matching 'patterns_to_remove_line' at the start are removed entirely.
    - For lines not removed, prefixes matching 'patterns_to_strip_prefix' at the
      start are stripped.
    - Lines matching neither are kept as is.

    Args:
        input_file_path (str): Path to the original input file.
        output_file_path (str): Path to save the sanitized output file.
        patterns_to_remove_line (list): List of regex patterns; if a line starts
                                       with a match, the entire line is removed.
        patterns_to_strip_prefix (list): List of regex patterns; if a line starts
                                        with a match, the matching prefix is removed.

    Returns:
        str: The path to the sanitized output file if successful, None otherwise.
    """
    # Compile regex patterns once for efficiency within the loop.
    compiled_remove_patterns = [re.compile(p) for p in patterns_to_remove_line]
    compiled_strip_patterns = [re.compile(p) for p in patterns_to_strip_prefix]
    lines_written = 0
    try:
        # Use utf-8 encoding and ignore errors for broader compatibility with various log files.
        with open(input_file_path, 'r', encoding='utf-8', errors='ignore') as f_in, \
             open(output_file_path, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                processed_line = line # Start with the original line by default.
                skip_line = False

                # 1. Check if the entire line should be removed based on remove patterns.
                for pattern in compiled_remove_patterns:
                    if pattern.match(processed_line):
                        skip_line = True
                        break # Found a removal match, no need to check other removal patterns.
                if skip_line:
                    continue # Skip this line entirely and go to the next line.

                # 2. Check if a prefix should be stripped (only if the line wasn't skipped).
                prefix_stripped = False
                for pattern in compiled_strip_patterns:
                    # Use subn to replace only the first occurrence (prefix) and check if a substitution happened.
                    new_line, num_subs = pattern.subn('', processed_line, count=1)
                    if num_subs > 0:
                        processed_line = new_line
                        prefix_stripped = True
                        break # Assume only one prefix pattern should be stripped per line.

                # 3. Write the processed line (original or stripped) to the output file.
                f_out.write(processed_line)
                lines_written += 1

        print(f"Sanitized file created: {output_file_path} ({lines_written} lines written)")
        return output_file_path
    except FileNotFoundError:
        # This error specifically relates to the input file not being found.
        print(f"Error: Input file not found for sanitization: {input_file_path}")
        return None
    except Exception as e:
        # This generic exception likely occurs during writing to the output file.
        print(f"Error during file sanitization (writing to '{output_file_path}'): {e}")
        return None

def process_file(input_file, add_line_number=True, add_tags=True, tags_to='both', ignore_empty_lines=False,
                 case_sensitive=True, keep_empty_duplicates=False, disable_line_number=False, disable_tags=False):
    """
    Processes a (typically sanitized) file to identify unique and duplicate lines,
    optionally adding line numbers and UNQ/DUP tags. Creates two output files:
    one with all processed lines ('-MARKED') and one with only unique lines ('-UNIQUE')
    (behavior modified by 'tags_to' argument).

    Args:
        input_file (str): Path to the input file (should be the sanitized file).
        add_line_number (bool): Whether to add line numbers to the output.
        add_tags (bool): Whether to add UNQ/DUP tags to the output.
        tags_to (str): Determines where tags are applied ('both', 'marked', 'unique').
        ignore_empty_lines (bool): If True, empty lines are ignored for uniqueness checks.
        case_sensitive (bool): If True, uniqueness check is case-sensitive.
        keep_empty_duplicates (bool): If True, duplicate empty lines are kept in output.
        disable_line_number (bool): Overrides add_line_number, forcing numbers off.
        disable_tags (bool): Overrides add_tags, forcing tags off.
    """
    unique_lines = set() # Stores lines encountered so far for uniqueness checks.
    output_lines_marked = [] # Lines for the '-MARKED' output file.
    output_lines_unique = [] # Lines for the '-UNIQUE' output file.

    try:
        # Read the input file (expected to be the sanitized one).
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f_in:
            lines = f_in.readlines()
    except FileNotFoundError:
        print(f"Error: File not found: {input_file}")
        return
    except Exception as e:
        print(f"Error reading processed file {input_file}: {e}")
        return

    num_lines = len(lines)
    # Determine width for zero-padding line numbers based on total lines. Handle empty file case.
    line_number_width = len(str(num_lines)) if num_lines > 0 else 1
    line_number_format = f"{{:0{line_number_width}d}}" # e.g., "{:05d}" for 10000+ lines

    unique_line_counter = 0 # Counter for unique lines, used for numbering in the unique file.

    for i, line in enumerate(lines):
        original_line = line # Keep the line with original whitespace/newline.
        # Prepare line for uniqueness check: strip trailing newline, optionally lowercase.
        line_for_check = line.rstrip('\n')

        # Handle empty lines according to the 'ignore_empty_lines' flag.
        is_empty_line = not line_for_check
        if ignore_empty_lines and is_empty_line:
            continue # Skip processing this empty line entirely if flag is set.

        if not case_sensitive:
            line_for_check = line_for_check.lower()

        is_duplicate = line_for_check in unique_lines

        # Add to set of unique lines if not already present.
        if not is_duplicate:
            unique_lines.add(line_for_check)
            # Increment unique counter only when a new unique line is found.
            # This counter is used for numbering in the unique file output.
            unique_line_counter += 1

        # Decide whether to skip outputting this line based on duplication and emptiness flags.
        # Skip duplicate empty lines unless 'keep_empty_duplicates' is True.
        if is_duplicate and not keep_empty_duplicates and is_empty_line:
            continue

        # --- Build the line for the MARKED output file ---
        marked_line_parts = []
        # Add line number prefix if enabled.
        if not disable_line_number:
            line_number_str = line_number_format.format(i + 1) # Use original file line number.
            marked_line_parts.append(f"[{line_number_str}]")

        # Determine and add tag (UNQ/DUP) if enabled and applicable for marked file.
        tag = ''
        if not disable_tags:
            tag = 'DUP' if is_duplicate else 'UNQ'
            if tags_to == 'both' or tags_to == 'marked':
                if tag: # Append tag only if it's not empty (it always should be here).
                    marked_line_parts.append(tag)

        # Join prefix parts (line number, tag) with a space.
        marked_line_prefix = " ".join(marked_line_parts)
        # Add a space after the prefix only if the prefix is not empty.
        marked_line = f"{marked_line_prefix} " if marked_line_prefix else ""
        marked_line += original_line # Append the original line content.
        output_lines_marked.append(marked_line)

        # --- Build the line for the UNIQUE output file ---
        should_add_to_unique_output = False
        unique_tag_to_add = '' # Tag specifically for the unique file.

        # Determine if the line should be included in the unique output.
        if not is_duplicate:
            # Always add non-duplicate lines to the unique output.
            should_add_to_unique_output = True
            # Add 'UNQ' tag if tags are enabled and applicable for unique file.
            if not disable_tags and (tags_to == 'both' or tags_to == 'unique'):
                unique_tag_to_add = 'UNQ'
        elif is_duplicate and tags_to == 'unique' and not disable_tags:
            # Special case: Add duplicates to unique output only if tags_to='unique'
            # and tags are not disabled. This allows creating a file *only* showing duplicates.
            should_add_to_unique_output = True
            unique_tag_to_add = 'DUP'

        # Construct the line for unique output if it should be added.
        if should_add_to_unique_output:
            unique_line_parts = []
            # Add line number prefix if enabled, using a separate counter for unique file numbering.
            if not disable_line_number:
                # Use the count of lines already added to unique output for sequential numbering.
                unique_output_line_num_str = line_number_format.format(len(output_lines_unique) + 1)
                unique_line_parts.append(f"[{unique_output_line_num_str}]")

            # Add the determined tag (UNQ/DUP) if applicable.
            if unique_tag_to_add:
                unique_line_parts.append(unique_tag_to_add)

            # Join prefix parts and append original line content.
            unique_line_prefix = " ".join(unique_line_parts)
            unique_line = f"{unique_line_prefix} " if unique_line_prefix else ""
            unique_line += original_line
            output_lines_unique.append(unique_line)


    # --- Write Output Files ---
    # Base the output filenames on the input filename provided to this function (the sanitized one).
    base, ext = os.path.splitext(input_file)
    output_file_marked = f"{base}-MARKED{ext}"
    output_file_unique = f"{base}-UNIQUE{ext}"

    # Write the MARKED output file containing all processed lines.
    try:
        with open(output_file_marked, 'w', encoding='utf-8') as f_out_marked:
            f_out_marked.writelines(output_lines_marked)
        print(f"Processed file saved as: {output_file_marked}")
    except Exception as e:
        print(f"Error writing MARKED file '{output_file_marked}': {e}")

    # Write the UNIQUE output file containing unique lines (and potentially duplicates based on args).
    try:
        with open(output_file_unique, 'w', encoding='utf-8') as f_out_unique:
            # The logic above correctly prepared output_lines_unique based on arguments.
            f_out_unique.writelines(output_lines_unique)
        print(f"Unique lines saved as: {output_file_unique}")
    except Exception as e:
        print(f"Error writing UNIQUE file '{output_file_unique}': {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge files from a directory, sanitize the content by removing or stripping patterns, "
                    "and process the result to identify unique/duplicate lines with optional line numbers and tags."
    )
    parser.add_argument("input_path", help="Path to the input file or directory.")

    # Arguments specific to directory processing (merging)
    dir_group = parser.add_argument_group('Directory Processing Options')
    dir_group.add_argument("--include-extensions", nargs='+', default=['.log', '.txt'],
                           help="List of file extensions to merge (e.g., .log .txt). Default: .log .txt")
    dir_group.add_argument("--ignore-files", nargs='+', default=['*-MERGED_*.txt', '*-SANITIZED.*', '*-MARKED.*', '*-UNIQUE.*'],
                           help="List of filename patterns (wildcards *) to ignore during merging. Default ignores typical output files.")

    # Arguments for sanitization (applied after merging or to single file)
    # Note: Sanitization patterns are currently hardcoded below but could be made arguments.
    #       This section primarily defines the processing flags applied *after* sanitization.

    # Arguments for processing (applied after sanitization)
    proc_group = parser.add_argument_group('Sanitization and Processing Options')
    # Deprecated flags (use --disable-* flags instead or rely on default behavior)
    # proc_group.add_argument("--add-line-number", action="store_true", help="DEPRECATED: Add line numbers (default: True). Use --disable-line-number to turn off.")
    # proc_group.add_argument("--add-tags", action="store_true", help="DEPRECATED: Add UNQ/DUP tags (default: True). Use --disable-tags to turn off.")
    proc_group.add_argument("--tags-to", choices=['both', 'marked', 'unique'], default='both',
                            help="Apply tags to which output file ('both', 'marked', 'unique'). Default: 'both'.")
    proc_group.add_argument("--ignore-empty-lines", action="store_true",
                            help="Ignore empty lines when checking for uniqueness.")
    proc_group.add_argument("--case-sensitive", action=argparse.BooleanOptionalAction, default=True,
                            help="Perform case-sensitive comparisons (default). Use --no-case-sensitive for insensitive.")
    proc_group.add_argument("--keep-empty-duplicates", action="store_true",
                            help="Keep empty lines in the output even if they are duplicates.")
    proc_group.add_argument("--disable-line-number", action="store_true",
                            help="Disable adding line numbers to output files.")
    proc_group.add_argument("--disable-tags", action="store_true",
                            help="Disable adding UNQ/DUP tags to output files.")

    args = parser.parse_args()

    input_path = args.input_path
    file_to_process_after_merge = None # This will hold the path to the file to be sanitized/processed.

    # --- Step 1: Determine input type (file/directory) and potentially merge files ---
    if not os.path.exists(input_path):
        print(f"Error: Input path does not exist: {input_path}")
        exit(1)
    elif os.path.isdir(input_path):
        print(f"Input is a directory: {input_path}. Starting file merge...")
        merged_file = process_directory_input(
            input_path,
            args.include_extensions,
            args.ignore_files
        )
        if merged_file:
            file_to_process_after_merge = merged_file
            print(f"\nDirectory processing complete. Will now process merged file: {file_to_process_after_merge}")
        else:
            print("Directory processing failed or yielded no files to merge. Aborting.")
            exit(1)
    elif os.path.isfile(input_path):
        print(f"Input is a single file: {input_path}")
        # If input is a single file, it's the one we process directly.
        file_to_process_after_merge = input_path
    else:
        print(f"Error: Input path is neither a file nor a directory: {input_path}")
        exit(1)

    # --- Step 2: Sanitize the determined file (merged or single input) ---
    if file_to_process_after_merge:
        print(f"\nStarting sanitization for: '{file_to_process_after_merge}'...")
        base, ext = os.path.splitext(file_to_process_after_merge)
        sanitized_output_file = f"{base}-SANITIZED{ext}"

        # Define hardcoded regex patterns for sanitization.
        # Patterns that cause the entire line to be removed if matched at the start.
        patterns_to_remove_line = [
            r'^\s*\[\x1b\[\d+m[A-Z]+?\x1b\[0m\]', # Common ANSI color log level prefixes like [[34mINF[0m]
            # Add more patterns here for full line removal if needed.
        ]
        # Patterns where only the matching prefix is stripped from the start of the line.
        patterns_to_strip_prefix = [
            r'^\s*\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*', # Nuclei timestamp [YYYY-MM-DD HH:MM:SS]
            r'^\s*\[\d{2}:\d{2}:\d{2}\]\s*',                     # SQLMap timestamp [HH:MM:SS]
            r'^\s*[A-Z][a-z]{2}\s\d{2}\/\d{2}\/\d{4}\s+\d{1,2}:\d{2}:\d{2}\.\d{2}:\s*', # Example CMD timestamp
            # Common timestamp format (ISO 8601 variations) - uncomment or adapt if needed
            # r'^\s*\[\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\]\s*',
            # Common log level prefixes - uncomment or adapt if needed
            # r'^\s*(?:DEBUG|INFO|WARNING|ERROR|CRITICAL|TRACE|FATAL)\s*[:\-]\s*',
        ]

        # Perform the sanitization.
        sanitized_file_path = sanitize_file(
            file_to_process_after_merge,
            sanitized_output_file,
            patterns_to_remove_line,
            patterns_to_strip_prefix
        )

        # --- Step 3: Process the Sanitized File (adding line numbers/tags, finding duplicates) ---
        if sanitized_file_path:
            print(f"\nProcessing the sanitized file: '{sanitized_file_path}'...")

            # Pass the command-line arguments controlling processing behavior to process_file.
            # Note: --add-line-number and --add-tags are implicitly True unless disabled.
            process_file(
                sanitized_file_path,
                # Line numbers are added unless explicitly disabled.
                add_line_number=(not args.disable_line_number),
                # Tags are added unless explicitly disabled.
                add_tags=(not args.disable_tags),
                tags_to=args.tags_to,
                ignore_empty_lines=args.ignore_empty_lines,
                case_sensitive=args.case_sensitive,
                keep_empty_duplicates=args.keep_empty_duplicates,
                disable_line_number=args.disable_line_number,
                disable_tags=args.disable_tags
            )
            print("\nProcessing finished.")
        else:
            print("Processing aborted because the sanitization step failed.")
    else:
        # This case should not be reached due to earlier checks, but included for safety.
        print("Error: No valid file determined for processing.")
        exit(1)