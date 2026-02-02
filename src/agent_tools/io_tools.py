from mp_api.client import MPRester
import os
import shutil
from pathlib import Path
import warnings as warning


def copy_file(src_path, dest_path):
    """
    Copy a file from src_path to dest_path.
    """
    shutil.copy(src_path, dest_path)


def list_files(directory):
    """
    List all existing files in a directory.
    """
    return Path(directory).glob("*")


def write_file(file_path, content, safe=True):
    """
    Write content to a file. If safe is True, do not overwrite existing files.
    """
    if safe and Path(file_path).exists():
        warning.warn(f"File {file_path} already exists. Skipping write.")
    with open(file_path, "w") as f:
        f.write(content)


def fetch_structure_file(chemsys_formula_mpid, dest_dir):
    """
    Fetch structure file from Materials Project and save it to dest_dir.
    Save "MP_API_KEY" in your environment variables before using this function.

    Parameters
    ----------
    chemsys_formula_mpid : str
        The chemical system, formula, or Materials Project ID.
        (e.g., Li-Fe-O, Si-*, [Si-O, Li-Fe-P])
        (e.g., Fe2O3, Si*, [SiO2, BiFeO3])
        (e.g., mp-22526, [mp-22526, mp-149])
    dest_dir : str
        Directory to save the fetched structure files.
    """
    with MPRester() as mpr:
        entries = mpr.get_entries(chemsys_formula_mpid)

    for entry in entries:
        structure = entry.structure
        filename = f"{entry.entry_id}.cif"
        file_path = Path(dest_dir) / filename
        structure.to(filename=str(file_path))
