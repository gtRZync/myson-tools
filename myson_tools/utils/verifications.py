from .path_utils import normalize_id_with_text , get_barcode_value
from .io_utils import read_data_frame
from pathlib import Path
import sys

REFERENCE:dict[str, str] = {'T+': 'Tpos', 'T-': 'Tneg'}

def verify_folders_creation(main_dir: Path, excel_path: Path):
    df = read_data_frame(excel_path)
    if df is None:
        print("[ERROR] Dataframe is Empty, please verify the Excel file's content.")
        return

    df['normalized_patient'] = df['Patient'].apply(lambda x: normalize_id_with_text(x, REFERENCE, is_patient=True))

    # Build mapping: normalized_patient → list of barcodes
    patient_to_barcodes = {}
    for _, row in df.iterrows():
        pid = row['normalized_patient']
        barcode = row['Barcode']
        patient_to_barcodes.setdefault(pid, []).append(barcode)

    # Extract patient folder IDs that actually exist
    patient_folders = [item for item in main_dir.iterdir() if item.name.startswith("Patient_")]
    existing_patient_ids = set()
    for folder in patient_folders:
        raw_id = folder.name[len("Patient_"):]
        normalized_id = normalize_id_with_text(raw_id, REFERENCE, is_patient=True)
        existing_patient_ids.add(normalized_id)

    created_count = 0
    failed_count = 0

    print("\n📁 Verifying patient folders...\n")

    for patient_id, barcodes in patient_to_barcodes.items():
        folder_name = f"Patient_{patient_id}"
        if patient_id in existing_patient_ids:
            print(f"✅ {folder_name} exists. Associated barcodes: {barcodes}")
            created_count += 1
        else:
            print(f"❌ {folder_name} is missing. Expected for barcodes: {barcodes}")
            failed_count += 1


    total = created_count + failed_count
    print("\n📦 Summary:")
    if failed_count == 0:
        print(f"✅ All {total} folders were created successfully.\nFolder verification completed!")
        print("Proceeding to the next step...\n")
    elif created_count == 0:
        print("❌ No folders were found. Please run the '--create-folders' step.")
        sys.exit(1)
    else:
        print(f"⚠️ Partial success: {created_count} folders found, {failed_count} missing.")
        print("Please rerun the '--create-folders' script for the missing patients.\n")
        sys.exit(1)



def verify_renaming(folders_path: Path):
    all_items = list(folders_path.iterdir())

    sample_folders = [item for item in all_items if item.name.startswith("barcode")]

    failed_count = 0
    matched_count = 0
    not_renamed = []

    for sample in sample_folders:
        barcode_val = get_barcode_value(sample.name)
        if barcode_val == -1:
            print(f"❌ Could not extract barcode from sample folder name: {sample.name}")
            not_renamed.append(sample.name)
            failed_count += 1
            continue

        # Extract the normalized id part from the sample folder name 
        parts = sample.name.split('-', 1)
        if len(parts) < 2:
            print(f"❌ Sample folder '{sample.name}' does not contain expected '-' separator after barcode value")
            not_renamed.append(sample.name)
            failed_count += 1
            continue

        matched_count += 1

    if failed_count > 0:
        #FIXME: add check if __name__ == '__main__' to show what do :
            # either show to relauch cli_barcode_folder_renamer.py if name is __main__
            # else show to relaunch the option to rename folder (1)
        print("⚠️ At least one barcode folder wasn't renamed correctly. Please relaunch 'cli_barcode_folder_renamer.py' or rename manually.")
        print("Folders that weren't renamed correctly:")
        for folder in not_renamed:
            print(f"- {folder}")
        print(f"Total number of incorrectly renamed folders: {failed_count}.")
        sys.exit(1)
    else:
        print(f"✅ All {matched_count} barcode folders were successfully renamed.")
        print("Barcode verification completed.\nProceeding to the next step...\n")

