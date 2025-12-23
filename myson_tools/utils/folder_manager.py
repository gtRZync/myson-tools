from .path_utils import normalize_id_with_text, get_barcode_value
from .io_utils import read_data_frame
from .verifications import REFERENCE
from pathlib import Path
import pandas as pd
import numpy as np
import shutil


def create_patient_folders(base_path: Path, patient_ids: np.ndarray):
    if not base_path.is_dir():
        print(f"[ERROR] Folder path invalid: {base_path}")
        return

    all_created = True

    for pid in patient_ids:
        folder_name = "Patient_" + '_'.join(str(REFERENCE.get(word, word)) for word in pid.split())
        folder_path:Path = base_path / folder_name
        if folder_path.exists():
            print(f"[WARNING] Folder exists: {folder_name}")
            all_created = False
        else:
            try:
                folder_path.mkdir()
                print(f"[OK] Created folder: {folder_name}")
            except Exception as e:
                print(f"[ERROR] Failed creating folder {folder_name}: {e}")
                all_created = False

    if all_created:
        print("\n[SUCCESS] All folders created.")
    else:
        print("\n[WARNING] Some folders were not created (already existed or errors).")


def read_patient_ids(excel_path: Path):
    try:
        df = read_data_frame(excel_path)
        if df is None:
            return
        patient_ids = df["Patient"].dropna().unique()
        return patient_ids
    except Exception as e:
        print(f"[ERROR] Error reading Excel file: {e}")
        return
        

def sort_samples_to_patients(main_dir: Path, excel_path: Path):
    df = read_data_frame(excel_path)
    if df is None:
        print("[ERROR] Dataframe is Empty, please verify the Excel file's content.")
        return
    all_items = list(main_dir.iterdir())
    sample_folders = [item for item in all_items if item.is_dir() and item.name.startswith("barcode")]

    moved_count = 0
    failed_count = 0

    # Preprocess DataFrame columns
    df['Barcode'] = df['Barcode'].astype(int)
    df['ID échantillon'] = df['ID échantillon'].astype(str).str.strip()
    df['Patient'] = df['Patient'].astype(str).str.strip()

    df['normalized_id_full'] = df['ID échantillon'].apply(lambda x: normalize_id_with_text(x, REFERENCE, is_patient=False))
    df['normalized_patient'] = df['Patient'].apply(lambda x: normalize_id_with_text(x, REFERENCE, is_patient=True))

    for sample in sample_folders:
        sample_name = sample.name
        barcode_val = get_barcode_value(sample_name)

        if barcode_val == -1:
            print(f"[WARNING] Could not extract barcode from: {sample_name}")
            failed_count += 1
            continue

        match_df = df[df['Barcode'] == barcode_val]

        if match_df.empty:
            print(f"[WARNING] No match in DataFrame for barcode: {barcode_val} (from {sample_name})")
            failed_count += 1
            continue

        #? why ? because barcode values are generated in this format : barcodeXX with XX : {01, 02,..,10..}
        def normalize_barcode_val(x:int) -> (str | int): return f'0{x}' if x < 10 else x

        matched = False
        for _, row in match_df.iterrows():
            expected_sample_name = f"barcode{normalize_barcode_val(barcode_val)}-{row['normalized_id_full']}"
            print(f'sample : {sample_name}')
            print(f'expected : {expected_sample_name}')
            if expected_sample_name.lower() in sample_name.lower():
                pid = row['normalized_patient']
                patient_id = REFERENCE.get(pid, pid)
                dest_folder = main_dir / f"Patient_{patient_id}"
                dest_path = dest_folder / sample_name

                # Make sure destination folder exists
                dest_folder.mkdir(parents=True, exist_ok=True)

                try:
                    shutil.move(str(sample), str(dest_path))
                    print(f"[OK] Moved '{sample_name}' -> 'Patient_{patient_id}/'")
                    moved_count += 1
                except Exception as e:
                    print(f"[ERROR] Failed to move '{sample_name}': {e}")
                    failed_count += 1
                matched = True
                break

        if not matched:
            print(f"[WARNING] Barcode matched but no matching patient ID in folder name for {sample_name}")
            failed_count += 1

    total = moved_count + failed_count
    print("\n[SUMMARY]:")
    if failed_count == 0:
        print(f"[OK] All {total} samples moved successfully.")
    elif moved_count == 0:
        print(f"[ERROR] No samples moved. Please check your DataFrame or folder names.")
    else:
        print(f"[WARNING]  {moved_count} moved, {failed_count} failed to move.")


def rename_folder(old_path: Path, new_path: Path):
    try:
        old_path.rename(new_path)
        print(f"[OK] Renamed '{old_path.name}' to '{new_path.name}'")
    except FileNotFoundError:
        print(f"[ERROR] Folder '{old_path.name}' does not exist.")
    except FileExistsError:
        print(f"[ERROR] A file or folder with name '{new_path.name}' already exists.")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")


def rename_barcode_folders(main_path: Path, df: pd.DataFrame):
    if df.empty:
        print("[ERROR] DataFrame is empty. Please provide valid sample data.")
        return

    for folder in main_path.iterdir():
        if folder.is_dir() and 'barcode' in folder.name:
            barcode_value = get_barcode_value(folder.name)
            temp_df = df[df["Barcode"] == barcode_value]

            if temp_df.empty:
                print(f"[WARNING] No matching sample for barcode {barcode_value} (folder: {folder.name})")
                continue

            sample = str(temp_df["ID échantillon"].iloc[0]).strip()
            sample_parts = sample.split()
            final_sample = '-'.join(REFERENCE.get(p, p) for p in sample_parts)

            if final_sample in folder.name:
                print(f"[WARNING] Folder '{folder.name}' is already renamed.")
            else:
                new_folder_name = f"{folder.name}-{final_sample}"
                rename_folder(folder, main_path / new_folder_name)


