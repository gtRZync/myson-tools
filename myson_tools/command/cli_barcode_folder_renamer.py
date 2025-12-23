from myson_tools.utils import rename_barcode_folders
from myson_tools.utils import read_data_frame, get_paths
import argparse
import sys

ASCII_LOGO = r"""
██████╗  █████╗ ██████╗  ██████╗ ██████╗ ██████╗ ███████╗    ██████╗ ███████╗███╗   ██╗ █████╗ ███╗   ███╗███████╗██████╗ 
██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝    ██╔══██╗██╔════╝████╗  ██║██╔══██╗████╗ ████║██╔════╝██╔══██╗
██████╔╝███████║██████╔╝██║     ██║   ██║██║  ██║█████╗      ██████╔╝█████╗  ██╔██╗ ██║███████║██╔████╔██║█████╗  ██████╔╝
██╔══██╗██╔══██║██╔══██╗██║     ██║   ██║██║  ██║██╔══╝      ██╔══██╗██╔══╝  ██║╚██╗██║██╔══██║██║╚██╔╝██║██╔══╝  ██╔══██╗
██████╔╝██║  ██║██║  ██║╚██████╗╚██████╔╝██████╔╝███████╗    ██║  ██║███████╗██║ ╚████║██║  ██║██║ ╚═╝ ██║███████╗██║  ██║
╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
                simple barcode folders renamer tool
"""


def main():
    print(ASCII_LOGO)

    parser = argparse.ArgumentParser(description="Rename bacteria sample folders based on Excel data")
    parser.add_argument('-e', '--excel', help='Path to Excel file')
    parser.add_argument('-f', '--folder', help='Path to folder containing sample folders')
    parser.add_argument('-c', '--config', help='Path to config file (.conf)')

    args = parser.parse_args()
    try:
        excel_path, folder_path = get_paths(args)
        
        if excel_path is None and folder_path is None:
            sys.exit(1)

        if not excel_path or not excel_path.is_file():
            print(f"\n❌ Error: Excel file not found at: {excel_path}")
            sys.exit(1)

        if not folder_path or not folder_path.is_dir():
            print(f"\n❌ Error: Folder path not valid: {folder_path}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error while retrieving paths: {e}")
        sys.exit(1)
    
    try:
        df = read_data_frame(excel_path)
    except Exception as e:
        print(f"\n❌[ERROR] Error reading dataframe: {e}")
        sys.exit(1)
    
    if df is None:
        print("[ERROR] Dataframe is Empty, please verify the Excel file's content.")
        sys.exit(1)
    rename_barcode_folders(folder_path, df)

if __name__ == "__main__":
    main()
