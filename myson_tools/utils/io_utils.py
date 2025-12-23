from pathlib import Path
import configparser
import pandas as pd
import unicodedata
import argparse
import sys
import os

from typing import NoReturn
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

def read_data_frame(excel_path: Path):
    if excel_path.suffix.lower() not in [".xlsx", ".xls"]: 
        print("\n❌ Error: Please select a valid Excel file (.xlsx or .xls).")
        return
    required_cols = ["Patient", "ID échantillon", "Barcode"]
    if not excel_path.is_file():
        print(f"❌ Error: Excel file not found at: {excel_path}")
        sys.exit(1)
    try:
        df = pd.read_excel(excel_path)
        for col in required_cols:
            if col not in df.columns:
                print(f"❌ Error: column '{col}' is missing from the Excel file.")
                sys.exit(1)
        return df
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        sys.exit(1)

def load_config(config_path):
    config = configparser.ConfigParser()
    with open(config_path, encoding='utf-8') as f:
        config.read_file(f)
    return config['paths']['excel'].strip(), config['paths']['folder'].strip(), config['paths']['subfolder'].strip()


def normalize_path_str(path_str: str):
    # Remove quotes if any, strip whitespace, then normalize unicode
    if path_str is None:
        return None
    cleaned = path_str.strip().strip('"').strip("'")
    cleaned = unicodedata.normalize("NFC", cleaned)
    return os.path.normpath(cleaned)


def get_paths(args: argparse.Namespace):
    excel_path = None
    folder_path = None

    if args.config:
        config_path = Path(args.config)
        if not config_path.is_file():
            print(f"\n❌ Error: Config file not found at: {args.config}")
            return None, None

        excel_cfg, folder_cfg, subfolder_cfg = load_config(config_path)

        folder_cfg_str = normalize_path_str(folder_cfg)
        subfolder_cfg_str = normalize_path_str(subfolder_cfg)
        excel_cfg_str = normalize_path_str(excel_cfg)

        if folder_cfg_str is None or subfolder_cfg_str is None or excel_cfg_str is None:
            print("\n❌ Error: Config file contains invalid paths.")
            return None, None

        folder_cfg_path = Path(folder_cfg_str) / subfolder_cfg_str
        excel_cfg_path = Path(excel_cfg_str)

    else:
        folder_cfg_path = None
        excel_cfg_path = None

    # Prefer CLI args, fall back to config
    excel_arg_str = normalize_path_str(args.excel) if args.excel else None
    folder_arg_str = normalize_path_str(args.folder) if args.folder else None

    if excel_arg_str is not None:
        excel_path = Path(excel_arg_str)
    elif excel_cfg_path is not None:
        excel_path = excel_cfg_path

    if folder_arg_str is not None:
        folder_path = Path(folder_arg_str)
    elif folder_cfg_path is not None:
        folder_path = folder_cfg_path

    if not excel_path or not folder_path:
        print("\n❌ Error: Must provide both Excel and folder paths via CLI or config.")
        return None, None

    return excel_path, folder_path
    
    
def env_var_missing(var_name: str, err_stream: Console) -> NoReturn:
    """Display a pretty error for missing environment variable and exit."""
    env_path = Path(__file__).parent.parent.parent / '.env'
    
    title_text = Text("❌ Environment Variable Missing", style="bold red")
    body_text = Text()
    body_text.append("The environment variable")
    body_text.append(f" {var_name} ", style="bold yellow")
    body_text.append("is not set.\n", style="white")
    body_text.append("Please update the .env file at:\n  ")
    body_text.append(f"{env_path}", style="bold yellow")
    body_text.append("\nwith the correct value and relaunch the tool.\n", style="white")
    body_text.append(f"Example: {var_name}=<path_here>", style="italic cyan")
    
    panel = Panel(body_text, title=title_text, border_style="red", expand=False)
    err_stream.print(panel)
    
    sys.exit(1)  

