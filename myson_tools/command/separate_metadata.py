import argparse
import logging
import os
import re
import sys
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.text import Text

from myson_tools.utils import REFERENCE
from myson_tools.utils.io_utils import env_var_missing

ASCII_LOGO = r"""
███████╗███████╗██████╗  █████╗ ██████╗  █████╗ ████████╗███████╗
██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
███████╗█████╗  ██████╔╝███████║██████╔╝███████║   ██║   █████╗
╚════██║██╔══╝  ██╔═══╝ ██╔══██║██╔══██╗██╔══██║   ██║   ██╔══╝
███████║███████╗██║     ██║  ██║██║  ██║██║  ██║   ██║   ███████╗
╚══════╝╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

███╗   ███╗███████╗████████╗ █████╗ ██████╗  █████╗ ████████╗ █████╗
████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗
██╔████╔██║█████╗     ██║   ███████║██║  ██║███████║   ██║   ███████║
██║╚██╔╝██║██╔══╝     ██║   ██╔══██║██║  ██║██╔══██║   ██║   ██╔══██║
██║ ╚═╝ ██║███████╗   ██║   ██║  ██║██████╔╝██║  ██║   ██║   ██║  ██║
╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝
                A script to easily separate metadata
                    Developer : Myson Dio
"""

#FIXME: remove logging usage
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

console = Console()
console_err = Console(stderr=True)

# A palette that feels rounded and smooth in transition
colors = [
    "#66CCFF",  # soft blue
    "#9966CC",  # lavender
    "#FF99CC"   # rose pink
]

def gradient_text(text: str, colors: list[str]) -> Text:
    result = Text()
    n = len(text)
    for i, char in enumerate(text):
        frac = i / max(n - 1, 1)
        idx = int(frac * (len(colors) - 1))
        next_idx = min(idx + 1, len(colors) - 1)
        local_frac = (frac * (len(colors) - 1)) - idx

        def hex_to_rgb(h): return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        def rgb_to_hex(rgb): return "#{:02x}{:02x}{:02x}".format(*rgb)

        c1 = hex_to_rgb(colors[idx].lstrip("#"))
        c2 = hex_to_rgb(colors[next_idx].lstrip("#"))

        interpolated = tuple(int(c1[j] + (c2[j] - c1[j]) * local_frac) for j in range(3))
        result.append(char, style=f"bold {rgb_to_hex(interpolated)}")

    return result


def parge_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(description='A script to create metadata.tsv file for samples')

    parser.add_argument(
        '-p', '--folder-path',
        type=str,
        required=True,
        default=None,
        help='This is refer to the folders where the Patients folders are located in.'
    )
    parser.add_argument(
            '--force',
            action='store_true',
            help='Force overwrite if metadata file already exists.'
    )

    return parser.parse_args()

def create_empty_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df_empty =  df.iloc[0:0]
    df_empty.insert(0, '#SampleID', [])
    return df_empty

def load_excel_as_df(filepath: Path) -> pd.DataFrame:
    if not filepath.exists():
        logging.error(f"❌ File does not exist: {filepath}")
        sys.exit(1)

    if not filepath.is_file():
        logging.error(f"❌ Path is not a file: {filepath}")
        sys.exit(1)

    try:
        df = pd.read_excel(filepath)
        logging.info(f"📄 Successfully loaded Excel file: {filepath}")
        return df
    except Exception as e:
        logging.error(f"❌ Failed to read Excel file: {filepath} — {e}")
        sys.exit(1)


def format_and_save_to_tsv(path: Path, excel_path: Path, metadata_output: Path, args: argparse.Namespace) -> None:
    savefile = f"{Path(args.folder_path).name}_sample-metadata.tsv"
    metadata_tsv = Path(metadata_output) / savefile
    if metadata_tsv.exists() and not args.force:
        print("Metadata file already exists.")
        print("Use --force to overwrite.")
        sys.exit(1)
    if not path.exists():
        logging.error(f"❌ Path does not exist: {path}")
        sys.exit(1)
    elif not path.is_dir():
        logging.error(f"❌ Path is not a directory: {path}")
        sys.exit(1)
    data = format_data(folder_path=path, df=load_excel_as_df(excel_path))
    data.to_csv(metadata_tsv, sep='\t', index=False, encoding='utf-8')
    console.print(f'✅Successfully created file : {savefile} at : {metadata_tsv.parent}')


def format_data(folder_path: Path, df: pd.DataFrame) -> pd.DataFrame:
    folder:Path
    barcode:Path
    new_dataframe: pd.DataFrame = create_empty_dataframe(df)
    reference_tags = set(REFERENCE.values())
    for folder in folder_path.iterdir():
        if folder.is_dir() and 'Patient' in folder.name:
            match = re.search(r'Patient_(\w+)', folder.name)
            if match:
                patient_id = match.group(1)
            else:
                console_err.print(f"Error while retrieving {folder.name} ID's.")
                continue
            if any(tag in patient_id for tag in reference_tags):
                logging.info(f"⏭️ Reference patient '{patient_id}' detected — skipping metadata entry.")
                continue
            print(f"📁 Processing Metadata for: {folder.name}")
            for barcode in folder.iterdir():
                if barcode.is_dir() and 'barcode' in barcode.name:
                    sample_id = barcode.name
                    if "#patientID" not in df.columns:
                        logging.error("❌ Required column '#patientID' is missing from the Excel file.")
                        sys.exit(1)
                    rows_to_add = df[df["#patientID"] == patient_id].copy()
                    if rows_to_add.empty:
                        logging.warning(f"⚠️ Unable to create dataframe: No data found for patient ID: {patient_id}")
                        continue
                    rows_to_add["#SampleID"] = sample_id
                    new_dataframe = pd.concat([new_dataframe, rows_to_add], ignore_index=True)
                    console.print(f"🧬 Metadata for sample '{sample_id}' added successfully.")
    if new_dataframe.empty:
        logging.warning("⚠️ No matching patient IDs found in the source metadata file. Metadata DataFrame is empty — no metadata file will be created.")
        sys.exit(1)
    return new_dataframe

if __name__ == '__main__':
    arg = parge_args()

    _base_dir=os.getenv('BASE_DIR')
    if _base_dir is None:
        env_var_missing(
            'BASE_DIR',
            console_err
        )
    _workdir=os.getenv('DEFAULT_WORK_DIR')
    if _workdir is None:
        env_var_missing(
            'DEFAULT_WORK_DIR',
            console_err
        )
    _metadata_folder=os.getenv('METADATA_PATH')
    if _metadata_folder is None:
        env_var_missing(
            var_name='METADATA_PATH',
            err_stream=console_err
        )
    _metadata_excel=os.getenv('METADATA_EXCEL_FILE')
    if _metadata_excel is None:
        env_var_missing(
            var_name='METADATA_EXCEL_FILE',
            err_stream=console_err
        )

    console.print(gradient_text(ASCII_LOGO, colors))
    final_path = Path(_base_dir) / Path(arg.folder_path) / _workdir
    metadata_path = Path(_metadata_folder) 
    excel_file = Path(_metadata_excel) 
    format_and_save_to_tsv(path=final_path, excel_path=excel_file, metadata_output=metadata_path, args=arg)
