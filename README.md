# llm-tools

A scipt for compiling code/text files and optionally a git commit (diff) in a repository to a single text file, and finally copy it to the clipboard for convenience. It is useful for interaction with LLMs, like the o1 model series by OpenAI.

It allows you to interactively select the files to include. If a commit is selected, files touched by that commit are preselected. Files/folders/patterns mentioned in .gitignore will be automatically excluded.

Usage examples:

`python /path/to/repo --commit "HEAD~1" -m "Review the code changes in this commit. Make sure to comment all errors and typos.`

`python /path/to/repo -m "Study the refactoring I did in this commit. Now please apply similar changes to OtherClass.`

`python /path/to/repo --extensions .md .py --no-diff -m "Check for any discrepancies between the code and the documentation. Also comment any grammar errors."`
