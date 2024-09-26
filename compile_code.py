#!/usr/bin/env python3

import os
import argparse

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Compile all .py files from a specified directory into a single file.')
    parser.add_argument('path', type=str, help='Path to the repository')
    parser.add_argument('-o', '--output', type=str, default='code.txt', help='Output file name (default: code.txt)')
    parser.add_argument('-e', '--exclude', nargs='*', default=[], help='List of directories to exclude')

    args = parser.parse_args()

    # Get the absolute path of the repository
    repo_path = os.path.abspath(args.path)
    output_file = args.output
    excluded_dirs = set(args.exclude)

    # Open the output file in write mode
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Walk through the directory tree
        for root, dirs, files in os.walk(repo_path):
            # Modify dirs in-place to exclude specified directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    # Compute the relative file path
                    relative_path = os.path.relpath(file_path, repo_path)
                    # Write the relative file path to the output file
                    outfile.write(f"{relative_path}\n")
                    # Wrap the file content in triple backticks
                    outfile.write('```\n')
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                    outfile.write('\n```\n\n')  # Close the code block and add separation

if __name__ == '__main__':
    main()
