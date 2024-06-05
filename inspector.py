import os
import re
import sys

import os
import re


def insert_print(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    modified_lines = []
    insert_print_next_line = False

    waiting_for_colon = False
    def_indentation = 0
    imported_inspect = False
    code = "print('ABCDE', inspect.stack()[1][3] if len(inspect.stack()) > 0 else 'N', self.__class__.__name__  if 'self' in locals() else 'F', inspect.currentframe().f_code.co_name, )\n"
    # inspect.stack()[1][3] if len(inspect.stack()) > 0 else 'N'\n)"
    for line in lines:
        # Skip lines starting with '#' or containing only whitespace followed by '#'
        if re.match(r'^\s*#', line):
            modified_lines.append(line)
            continue

        if not imported_inspect:
            modified_lines.append("import inspect\n")
            imported_inspect = True

        if waiting_for_colon and ":" in line:
            modified_lines.append(line)
            modified_lines.append(f"{' ' * def_indentation}    " + code)
            waiting_for_colon = False
        elif line.lstrip().startswith("def ") and ":" in line:
            modified_lines.append(line)
            indentation = len(line) - len(line.lstrip())
            modified_lines.append(f"{' ' * indentation}    " + code)
        elif line.lstrip().startswith("def "):
            modified_lines.append(line)
            waiting_for_colon = True
            def_indentation = len(line) - len(line.lstrip())
        else:
            modified_lines.append(line)

    with open(file_path, 'w') as file:
        file.writelines(modified_lines)


def process_files(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                insert_print(file_path)


# Example usage
directory_path = sys.argv[1]  # Specify the directory path here
process_files(directory_path)
