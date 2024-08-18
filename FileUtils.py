# Corrected code

import importlib
import inspect
import os
import pkgutil


def find_functions_in_package(package_name):
    """Search through every module in a package and pull out every function."""
    all_functions = {}

    package = importlib.import_module(package_name)
    for importer, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        module = importlib.import_module(modname)
        functions = {}

        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj):
                functions[name] = obj

        if functions:
            all_functions[modname] = functions

    return all_functions


def find_functions_in_all_packages(directory):
    """Search through every package in a directory and pull out every function."""
    all_functions = {}

    packages = find_packages_in_directory(directory)
    for package_name in packages:
        package_functions = find_functions_in_package(package_name)
        all_functions.update(package_functions)

    return all_functions


def find_packages_in_directory(directory):
    """Find all packages in the given directory."""
    packages = []

    for root, dirs, files in os.walk(directory):
        if "__init__.py" in files:
            # Convert the directory structure to a package name
            package = root.replace(directory, "").replace(os.path.sep, ".").strip(".")
            if package:
                packages.append(package)

    return packages


# Example usage:
directory_path = "."  # assuming you want to find packages in the current directory
functions = find_functions_in_all_packages(directory_path)
for module_name, funcs in functions.items():
    print(f"Module: {module_name}")
    for func_name, fn_obj in funcs.items():
        print(f"  Function: {func_name}")
