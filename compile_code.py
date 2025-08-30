import argparse
import dataclasses
import os
import subprocess

import pathspec
import pyperclip
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Box, CheckboxList, Frame
from prompt_toolkit.filters import has_focus


@dataclasses.dataclass
class Choice:
    title: str
    checked: bool


def checkbox_with_paging(message: str, choices: list[Choice]):
    values = [(c.title, c.title) for c in choices]
    cb_list = CheckboxList(values=values)

    kb = KeyBindings()

    @kb.add("pageup", filter=has_focus(cb_list))
    def _(event):
        cb_list._selected_index = max(0, cb_list._selected_index - 10)

    @kb.add("pagedown", filter=has_focus(cb_list))
    def _(event):
        cb_list._selected_index = min(
            len(cb_list.values) - 1, cb_list._selected_index + 10
        )

    @kb.add("enter", filter=has_focus(cb_list), eager=True)
    def _(event):
        event.app.exit(result=cb_list.current_values)

    @kb.add("escape")
    def _(event):
        event.app.exit(result=[])

    @kb.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt())

    root = HSplit(
        [
            Window(FormattedTextControl(message), height=1, dont_extend_height=True),
            Box(Frame(cb_list), padding=1),
        ]
    )

    app = Application(
        layout=Layout(root, focused_element=cb_list),  # focus the list at start
        key_bindings=kb,
        mouse_support=True,
        full_screen=True,
    )
    return app.run()


def main():
    parser = argparse.ArgumentParser(
        description="Compile selected files from a specified directory into a single file."
    )
    parser.add_argument("path", type=str, help="Path to the repository")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="code.txt",
        help="Output file name (default: code.txt)",
    )
    parser.add_argument(
        "-e", "--exclude", nargs="*", default=[], help="List of directories to exclude"
    )
    parser.add_argument(
        "-m",
        "--message",
        type=str,
        help="Message to append at the end of the output file",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".py", ".md", ".ini", ".yml", ".rs", ".toml", ".cpp", ".hpp"],
        help="List of file extensions to include (default: .py, .md, .ini, .yml, .rs, .toml, .cpp, .hpp)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include all files, ignoring extensions",
    )
    parser.add_argument(
        "--commit",
        type=str,
        default="HEAD~1",
        help="Git commit to use for the diff (default: HEAD~1)",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Include the git diff in the output and disregard the commit",
    )

    args = parser.parse_args()

    repo_path = os.path.abspath(args.path)
    output_file = args.output
    excluded_dirs = set(args.exclude)
    extensions = args.extensions
    commit = args.commit

    if not args.all:
        extensions = [ext if ext.startswith(".") else "." + ext for ext in extensions]

    gitignore_path = os.path.join(repo_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            gitignore_content = f.read()
        spec = pathspec.PathSpec.from_lines(
            "gitwildmatch", gitignore_content.splitlines()
        )
    else:
        spec = None

    candidate_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for file in files:
            if args.all or any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                # Compute the path relative to repo root
                relative_path = os.path.relpath(file_path, repo_path)
                relative_path = os.path.normpath(relative_path)
                # Check if file is ignored by .gitignore
                if spec and spec.match_file(relative_path):
                    continue  # Skip ignored files
                candidate_files.append(relative_path)

    if not candidate_files:
        print("No candidate files found.")
        return

    preselected_files = set()

    # Only get the list of changed files if not omitting the diff
    if args.diff:
        try:
            original_cwd = os.getcwd()
            os.chdir(repo_path)

            result = subprocess.run(
                ["git", "diff", "--name-only", commit],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                print("Error getting list of changed files:", result.stderr)
                changed_files = []
            else:
                changed_files = result.stdout.strip().split("\n")

            changed_files_relative = [os.path.normpath(f) for f in changed_files]

            os.chdir(original_cwd)

            # Filter changed files to include only candidate files with specified extensions
            preselected_files = {
                f
                for f in changed_files_relative
                if f in candidate_files
                and (args.all or any(f.endswith(ext) for ext in extensions))
            }

        except Exception as e:
            print(f"Error obtaining list of changed files: {e}")
            preselected_files = set()
    else:
        # If diff is omitted, disregard the commit and do not preselect any files
        preselected_files = set()

    # Create choices for the checkbox prompt, without pre-selecting any files if diff is omitted
    choices = [
        Choice(title=file, checked=(file in preselected_files))
        for file in candidate_files
    ]

    # Interactive selection of files
    selected_files = checkbox_with_paging(
        "Select the files to include in the output (use space to select, enter to confirm):",
        choices=choices,
    )

    if not selected_files:
        print("No files selected. Exiting.")
        return

    with open(output_file, "w", encoding="utf-8") as outfile:
        for relative_path in selected_files:
            file_path = os.path.join(repo_path, relative_path)

            outfile.write(f"{relative_path}\n")

            file_extension = os.path.splitext(relative_path)[1]
            language = ""
            if file_extension == ".py":
                language = "python"
            elif file_extension == ".md":
                language = "markdown"
            elif file_extension == ".txt":
                language = "plaintext"

            outfile.write(f"```{language}\n")
            try:
                with open(file_path, "r", encoding="utf-8") as infile:
                    outfile.write(infile.read())
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
            outfile.write("\n```\n\n")  # Close the code block and add separation

        # Append the diff of the specified git commit if not omitted
        if args.diff:
            try:
                os.chdir(repo_path)

                result = subprocess.run(
                    ["git", "diff", commit],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if result.returncode != 0:
                    print("Error getting git diff:", result.stderr)
                    diff_output = ""
                else:
                    diff_output = result.stdout

                os.chdir(original_cwd)

                outfile.write(f"This is the diff of the commit '{commit}':\n")
                outfile.write("```\n")
                outfile.write(diff_output)
                outfile.write("\n```\n")

            except Exception as e:
                print(f"Error obtaining git diff: {e}")
                outfile.write("Error obtaining git diff.\n")

        # Append the user-provided message at the end
        if args.message:
            outfile.write("\n")
            outfile.write(args.message)
            outfile.write("\n")

    with open(output_file, "r", encoding="utf-8") as file:
        pyperclip.copy(file.read())

    print("The text has been copied to the clipboard")


if __name__ == "__main__":
    main()
