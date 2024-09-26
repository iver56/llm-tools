#!/usr/bin/env python3

import os
import argparse
import subprocess

def main():
    try:
        import questionary
    except ImportError:
        print("The 'questionary' library is required for interactive file selection.")
        print("Please install it using 'pip install questionary' and try again.")
        return

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Compile selected .py files from a specified directory into a single file.')
    parser.add_argument('path', type=str, help='Path to the repository')
    parser.add_argument('-o', '--output', type=str, default='code.txt', help='Output file name (default: code.txt)')
    parser.add_argument('-e', '--exclude', nargs='*', default=[], help='List of directories to exclude')
    parser.add_argument('-m', '--message', type=str, help='Message to append at the end of the output file')

    args = parser.parse_args()

    # Get the absolute path of the repository
    repo_path = os.path.abspath(args.path)
    output_file = args.output
    excluded_dirs = set(args.exclude)

    # Collect all candidate .py files
    candidate_files = []
    for root, dirs, files in os.walk(repo_path):
        # Modify dirs in-place to exclude specified directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                # Compute the relative file path
                relative_path = os.path.relpath(file_path, repo_path)
                candidate_files.append(relative_path)

    # Interactive selection of files
    selected_files = questionary.checkbox(
        "Select the files to include in the output (use space to select, enter to confirm):",
        choices=candidate_files
    ).ask()

    if not selected_files:
        print("No files selected. Exiting.")
        return

    # Open the output file in write mode
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for relative_path in selected_files:
            file_path = os.path.join(repo_path, relative_path)
            # Write the relative file path to the output file
            outfile.write(f"{relative_path}\n")
            # Wrap the file content in triple backticks with language identifier
            outfile.write('```python\n')
            try:
                with open(file_path, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
            outfile.write('\n```\n\n')  # Close the code block and add separation

        # Append the diff of the latest git commit
        try:
            # Change current working directory to repo_path
            original_cwd = os.getcwd()
            os.chdir(repo_path)

            # Get the diff of the latest commit
            result = subprocess.run(['git', 'diff', 'HEAD~1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print("Error getting git diff:", result.stderr)
                diff_output = ''
            else:
                diff_output = result.stdout

            # Change back to original directory
            os.chdir(original_cwd)

            # Write the diff to the output file
            outfile.write("This is the diff of the latest commit:\n")
            outfile.write('```\n')
            outfile.write(diff_output)
            outfile.write('\n```\n')

        except Exception as e:
            print(f"Error obtaining git diff: {e}")
            outfile.write("Error obtaining git diff.\n")

        # Append the user-provided message at the end
        if args.message:
            outfile.write("\n")
            outfile.write(args.message)
            outfile.write("\n")

if __name__ == '__main__':
    main()
