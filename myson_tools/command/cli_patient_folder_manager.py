from myson_tools.utils import create_patient_folders, read_patient_ids, sort_samples_to_patients
from myson_tools.utils import verify_folders_creation, verify_renaming
from myson_tools.utils import get_paths
import argparse
import sys

ASCII_ART = r"""
██████╗  █████╗ ████████╗██╗███████╗███╗   ██╗████████╗    ███╗   ███╗ █████╗ ███╗   ██╗ █████╗  ██████╗ ███████╗██████╗ 
██╔══██╗██╔══██╗╚══██╔══╝██║██╔════╝████╗  ██║╚══██╔══╝    ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔════╝ ██╔════╝██╔══██╗
██████╔╝███████║   ██║   ██║█████╗  ██╔██╗ ██║   ██║       ██╔████╔██║███████║██╔██╗ ██║███████║██║  ███╗█████╗  ██████╔╝
██╔═══╝ ██╔══██║   ██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██║╚██╔╝██║██╔══██║██║╚██╗██║██╔══██║██║   ██║██╔══╝  ██╔══██╗
██║     ██║  ██║   ██║   ██║███████╗██║ ╚████║   ██║       ██║ ╚═╝ ██║██║  ██║██║ ╚████║██║  ██║╚██████╔╝███████╗██║  ██║
╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
            Patient folders manager tool 
"""

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Patient Folder Manager CLI\n" + ASCII_ART,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-c", "--config",
        help="Path to config file with [paths] section (excel, folder)"
    )
    parser.add_argument(
        "-e", "--excel",
        help="Path to the Excel file containing patient data"
    )
    parser.add_argument(
        "-f", "--folder",
        help="Path to base folder where patient folders will be created"
    )
    parser.add_argument(
        "--create-folders",
        action="store_true",
        help="Create patient folders based on Excel data"
    )
    parser.add_argument(
        "--list-patients",
        action="store_true",
        help="Just list patient IDs found in Excel file"
    )
    parser.add_argument(
        "--sort-samples",
        action="store_true",
        help="Sort sample files into patient folders"
    )
    return parser.parse_args()


def main():
    print(ASCII_ART.strip())
    args = parse_args()

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

    patient_ids = read_patient_ids(excel_path)
    
    if patient_ids is None:
        print("[ERROR] No patient ID found in Excel file.")
        sys.exit(1)
    
    if args.list_patients:
        print("\n📋 Patient IDs found:")
        for pid in patient_ids:
            print(f" - {pid}")
        print(f'Total number of unique patient IDs : {len(patient_ids)}.')
        return

    if args.create_folders:
        if not folder_path:
            print("❌ Folder path is required to create folders (via --folder or --config).")
            sys.exit(1)
        verify_renaming(folder_path)
        create_patient_folders(folder_path, patient_ids)

    elif args.sort_samples:
        if not folder_path:
            print("❌ Folder path is required to sort samples (via --folder or --config).")
            sys.exit(1)
        try:
            verify_folders_creation(folder_path, excel_path)
            sort_samples_to_patients(folder_path, excel_path)
            print("\n✅ Samples sorted successfully!")
        except Exception as e:
            print(f"❌ Error during sorting samples: {e}")

    else:
        print("⚠️ No action requested. Use --create-folders, --sort-samples, or --list-patients.")

if __name__ == "__main__":
    main()

