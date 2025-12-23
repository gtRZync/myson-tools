from rich.logging import RichHandler
from pathlib import Path
import argparse
import logging
import shutil
import sys
import re


LEVELS:list = ['level4', 'level5', 'level6', 'level7']
FREQUENCY:list = ['relfreq', 'absfreq']
TAXONOMY_FILENAME:str = 'taxonomy.qza'
EXTENSION:str = '.qza'
REFERENCE:list = ['Tpos','Tneg']

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(markup=True, show_time=False, show_level=False, show_path=False)]
)
log = logging.getLogger("rich")

#add an optional outpout folder to this script if it's not given the folders will be created in the working dir (modify myson_tools.py accordingly for the prompt)

def create_output_folders(output_dir: Path ) -> None:
    base_dir = output_dir if output_dir else Path.cwd()
    for level in LEVELS:
        for freq in FREQUENCY:
            folder_name = base_dir / f'{freq}_{level}'
            if not folder_name.exists():
                folder_name.mkdir(parents=True)




def get_run_name(path: Path) -> (str | None):
    match = re.search((r'(\d{6})_ICMc'), str(path))
    return match.group(0) if match else None

def new_file_name(root_folder: Path, filename:str) -> str:
    pid = root_folder.name.split('_', 2)[2]
    if any(ref in pid for ref in REFERENCE):
        return f'{filename.removesuffix(EXTENSION)}-{get_run_name(root_folder)}_{pid}{EXTENSION}'
    else:
        return f'{filename.removesuffix(EXTENSION)}-{pid}{EXTENSION}'

def to_plural_if_needed(x:int, string:str) -> str:
    return f'{string}s' if x > 1 and not string.endswith('s') else string


def verify_files_existence(path: Path) -> None:
    table_success:int = 0
    taxonomy_success:int = 0
    files_checked:int = 0
    folders_skipped:int = 0
    skipped_folder:dict = {}

    if not path.exists() or not path.is_dir():
        print(f"[ERROR] The path {path} is invalid. Please check the directory.", file=sys.stderr)
        sys.exit(1)

    for folder in path.iterdir():
        if folder.is_dir() and 'Result' in folder.name:
            collapse_folder = next(
                (f for f in folder.iterdir() if f.is_dir() and 'collapseTables' in f.name),
                None
            )
            taxonomy_folder = next(
                (f for f in folder.iterdir() if f.is_dir() and 'assignTaxonomy' in f.name),
                None
            )

            if collapse_folder and taxonomy_folder:
                for level in LEVELS:
                    for freq in FREQUENCY:
                        target_sequence = Path(f'{freq}-{level}{EXTENSION}')

                        # Check files in collapseFolder
                        for table in collapse_folder.iterdir():
                            if target_sequence.name in table.name:
                                log.info("[bold green][OK][/bold green] File '%s' found at '%s'", table.name, table.parent)
                                table_success += 1
                            files_checked += 1

                        # Check for taxonomy file
                        for file in taxonomy_folder.iterdir():
                            if file.name == TAXONOMY_FILENAME:
                                log.info("[bold green][OK][/bold green] File '%s' found at '%s'", file.name, file.parent)
                                taxonomy_success += 1
                            files_checked += 1
            elif not collapse_folder and taxonomy_folder:
                log.info("[cyan][SKIP][/cyan] Folder collapseTables was not found for %s — Skipping copy.", folder.name)
                folders_skipped += 1
                skipped_folder[folder.name] = ' reason : Folder collapseTables not found.'
            else:
                log.info("[cyan][SKIP][/cyan] Folder assignTaxonomy was not found for %s — Skipping copy.", folder.name)
                folders_skipped += 1
                skipped_folder[folder.name] = ' reason : Folder assignTaxonomy not found.'

    total_found = table_success + taxonomy_success
    if total_found == 0 and files_checked > 0:
        log.warning("[yellow][WARNING][/yellow] No matching files found for the target levels.")
        sys.exit(1)
    elif total_found == 0 and files_checked == 0:
        log.warning("[yellow][WARNING][/yellow] No files found in the specified directory. Check the folder and file locations.")
        sys.exit(1)

    # Summary of results
    print('\n')
    log.info("[bold green][INFO][/bold green] Verification complete: %d %s checked.", files_checked, to_plural_if_needed(files_checked, 'file'))
    if taxonomy_success > 0:
        log.info("[bold green][OK][/bold green] %d taxonomy %s found.", taxonomy_success, to_plural_if_needed(taxonomy_success, 'file'))
    if table_success > 0:
        log.info("[bold green][OK][/bold green] %d collapsed %s found.", table_success, to_plural_if_needed(table_success, 'table'))
    if folders_skipped > 0:
        log.warning("[yellow][WARNING][/yellow] %d %s skipped : ", folders_skipped, to_plural_if_needed(folders_skipped, 'folder'))
        for key, value in skipped_folder.items():
            log.warning("[yellow]%s, reason : %s[/yellow]", key, value)



    print('\n')
    log.info("[bold green][INFO][/bold green] Proceeding to the file copy process.")
    log.info("[bold green][INFO][/bold green] Starting the transfer of target files to the custom (frequency_level/) destination folder.\nPlease wait while the operation completes...")
    print('\n\n')


def copy_files(path: Path, output_dir: Path) -> None:

    base_dir = output_dir

    if not path.exists() or not path.is_dir():
        print(f"[ERROR] The path {path} is invalid. Please check the directory.", file=sys.stderr)
        sys.exit(1)

    create_output_folders(output_dir)

    for folder in path.iterdir():
        if folder.is_dir() and 'Result' in folder.name:
            collapse_folder = next(
                (f for f in folder.iterdir() if f.is_dir() and 'collapseTables' in f.name),
                None
            )
            taxonomy_folder = next(
                (f for f in folder.iterdir() if f.is_dir() and 'assignTaxonomy' in f.name),
                None
            )
            if collapse_folder and taxonomy_folder:
                for level in LEVELS:
                    for freq in FREQUENCY:
                        folder_name = base_dir / f'{freq}_{level}'
                        target_sequence = Path(f'{folder_name.name.replace("_", "-")}{EXTENSION}')
                        folder_abs_path = folder_name.absolute()

                        if not folder_abs_path.exists():
                            log.info("[yellow][WARNING][/yellow] Folder %s was not created.", folder_name)
                            continue

                        for table in collapse_folder.iterdir():
                            if target_sequence.name in table.name:
                                table_output = folder_abs_path / new_file_name(folder, table.name)
                                try:
                                    shutil.copy(table, table_output)
                                    log.info("[bold green][OK][/bold green] Success: File '%s' was copied to '%s'", table.name, table_output)
                                except Exception as e:
                                    log.error("[bold red][ERROR][/bold red] %s", e)

                        for file in taxonomy_folder.iterdir():
                            if file.name == TAXONOMY_FILENAME:
                                taxonomy_output = folder_abs_path / new_file_name(folder, file.name)
                                try:
                                    shutil.copy(file, taxonomy_output)
                                    log.info("[bold green][OK][/bold green] Success: File '%s' was copied to '%s'", file.name, taxonomy_output)
                                except Exception as e:
                                    log.error("[bold red][ERROR][/bold red] %s", e)

            elif not collapse_folder and taxonomy_folder:
                log.info("[yellow][WARNING][/yellow] Folder collapseTables was not found for %s — Skipping copy.", folder.name)
                continue
            else:
                log.info("[yellow][WARNING][/yellow] Folder assignTaxonomy was not found for %s — Skipping copy.", folder.name)
                continue



def main() -> None:

    parser = argparse.ArgumentParser(
        description="""This script collects all '.qza' files from a specified directory.
        The script recursively searches through the given folder and identifies all
        files with the '.qza' extension, which are typically used in bioinformatics pipelines.
        It provides an easy way to gather and organize relevant QIIME 2 artifacts in one location.
        Users can specify the target folder as an input argument.
        The script will display a list of found files or an error message if no such files exist.
        """
        )
    parser.add_argument(
        '--folder',
        type=Path,
        required=True,
        default=None,
        help=(
            "Path to the '2_Result' folder that contains the sample analysis results. "
            "This folder is expected to hold the processed output files from the analysis. "
            "Please ensure that the folder contains the necessary files and is structured correctly, "
            "as this script will use these files for further processing. "
            "If the folder doesn't exist or the path is incorrect, an error will be raised."
        )
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=False,
        default=None,
        help="Optional output directory for the frequency_level folders. If not provided, folders will be created in the working directory."
    )
    args = parser.parse_args()
    verify_files_existence(args.folder)
    copy_files(args.folder, args.output)


if __name__ == '__main__':
    main()