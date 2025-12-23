import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from myson_tools.utils.io_utils import env_var_missing
from myson_tools.utils.path_utils import notify_missing_folder

BARCODE_LEVEL:str = "barcode_level"
PATIENT_LEVEL:str = "patient_level"
_workDir = Path
@dataclass(frozen=True, slots=True)
class _temporaryMoveState:
    success: bool

    @property
    def failed(self) -> bool:
        return not self.success

ASCII_LOGO = r'''
 █████╗ ██╗   ██╗████████╗ ██████╗ ███╗   ███╗ █████╗ ████████╗███████╗
██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
███████║██║   ██║   ██║   ██║   ██║██╔████╔██║███████║   ██║   █████╗
██╔══██║██║   ██║   ██║   ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝
██║  ██║╚██████╔╝   ██║   ╚██████╔╝██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

███╗   ███╗███████╗████████╗ ██████╗ ███╗   ██╗████████╗██╗██╗███╗   ███╗███████╗
████╗ ████║██╔════╝╚══██╔══╝██╔═══██╗████╗  ██║╚══██╔══╝██║██║████╗ ████║██╔════╝
██╔████╔██║█████╗     ██║   ██║   ██║██╔██╗ ██║   ██║   ██║██║██╔████╔██║█████╗
██║╚██╔╝██║██╔══╝     ██║   ██║   ██║██║╚██╗██║   ██║   ██║██║██║╚██╔╝██║██╔══╝
██║ ╚═╝ ██║███████╗   ██║   ╚██████╔╝██║ ╚████║   ██║   ██║██║██║ ╚═╝ ██║███████╗
╚═╝     ╚═╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝╚═╝     ╚═╝╚══════╝
                MetONTIIME Launcher - Run multiple samples easily
                        Developper : Myson Dio
'''

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


def parse_skip_arg(skip_args):
    """
    Allows the --skip argument to accept a list of items OR a single value starting with '@' to load from a file.
    """
    if len(skip_args) == 1 and skip_args[0].startswith('@'):
        filename = skip_args[0][1:]
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    else:
        return skip_args

def parse_args():
    parser = argparse.ArgumentParser(description="A script to automate a pipeline execution.")

    parser.add_argument(
        '-w', '--workDir',
        type=str,
        required=False,
        default='1_Raw_data/fastq_pass',
        help="Path where all the patient folders are located."
    )
    parser.add_argument(
        '-p', '--pathDir',
        type=str,
        required=True,
        help="Path where the 1_Raw_Data and the soon to be 2_Results folder are located."
    )
    parser.add_argument(
        '-m', '--metadata',
        nargs='?',
        const=True,
        default=False,
        help="Use dynamic metadata lookup based on working folder. If not provided, defaults to 'sample-metadata.tsv'."
    )
    parser.add_argument(
        '--resume',
        nargs='?',
        const='-resume',
        default=None,
        help="Activate Nextflow's -resume argument"
    )
    parser.add_argument(
        '--skip',
        type=str,
        default=None,
        nargs='+',
        help='List of run folders to skip (space-separated after --skip, or @file.txt for file input).'
    )
    parser.add_argument(
        '-l', '--level',
        type=str,
        default=None,
        required=True,
        help="This level argument helps figure which internal function to call, only the dev knows about it tho."
    )

    parser.add_argument(
        '-c', '--conf',
        type=str,
        default=None,
        required=True,
        help='The conf database that will be used by metontiime to perform its analysis'
    )

    args = parser.parse_args()

    args.skip = parse_skip_arg(args.skip) if args.skip else []

    return args

def set_resume_value(arg: argparse.Namespace):
    return '' if arg.resume is None else arg.resume

def metadata_caption(arg: argparse.Namespace) -> str:
    if arg.metadata is True:
        return "🔍 Using dynamically resolved metadata file"
    elif isinstance(arg.metadata, str):
        return f"📝 Using custom metadata file: {arg.metadata}"
    else:
        return "📄 Using default metadata file: sample-metadata.tsv"

def resolve_metadata_path(metadata_dir: Path, keyword: str, result_dir: Path) -> Path:
    for file in metadata_dir.iterdir():
        if file.is_file() and keyword in file.name:
            return file
    return result_dir / 'sample-metadata.tsv'

def set_metadata_path(metadata_dir: Path, keyword: str, args: argparse.Namespace, result_dir: Path) -> Path:
    if args.metadata is True:
        return resolve_metadata_path(metadata_dir, keyword, result_dir)
    elif isinstance(args.metadata, str):
        return result_dir / args.metadata
    else:
        return result_dir / 'sample-metadata.tsv'

def get_folder_count(workdir: Path, args: argparse.Namespace) -> int:
    if args.level == PATIENT_LEVEL:
        return len([p for p in workdir.iterdir() if p.is_dir() and 'patient' in p.name.lower() and (args.skip is None or p.name not in args.skip)])
    else:
        return len([p for p in workdir.iterdir() if p.is_dir() and 'barcode' in p.name.lower() and (args.skip is None or p.name not in args.skip)])

def skip_folders(args: argparse.Namespace):
    if args.skip:
        console.print("[bold yellow]Skipping folders:[/bold yellow]")
        for name in args.skip:
            console.print(f"• [cyan]{name}[/cyan]")

def reset_terminal():
    """Try to restore the terminal to a usable state."""
    if sys.platform != "win32":
        try:
            # This bypasses stdin and writes directly to the terminal device
            subprocess.run(["stty", "sane"], stdin=open("/dev/tty"), check=True)
            print("\033[?25h", end="")  # Ensure cursor is visible
        except Exception as e:
            console_err.print(f"[bold red][!] Failed to reset terminal:[/bold red] {e}")
            console_err.print("[bold cyan]Tip:[/bold cyan] Try typing `reset` and press Enter.")

def automate_analysis() -> None:
    args = parse_args()

    _base_dir=os.getenv('BASE_DIR')
    if _base_dir is None:
        env_var_missing(
            'BASE_DIR',
            console_err
        )
    _conf_path=os.getenv('CONF_PATH')
    if _conf_path is None:
        env_var_missing(
            var_name='CONF_PATH',
            err_stream=console_err
        )
    _metontiimescript=os.getenv('METONTIIME_SCRIPT')
    if _metontiimescript is None:
        env_var_missing(
            var_name='METONTIIME_SCRIPT',
            err_stream=console_err
        )
    _metadata_folder=os.getenv('METADATA_PATH')
    if _metadata_folder is None:
        env_var_missing(
            var_name='METADATA_PATH',
            err_stream=console_err
        )

    pathDir:Path = Path(_base_dir) / args.pathDir
    metontiimeScript = Path(_metontiimescript)
    confPath = Path(_conf_path) / args.conf
    workDir:Path = pathDir / args.workDir
    if not workDir.exists() or not workDir.is_dir():
        console_err.print(
            f"\n[bold red][ERROR][/bold red] The path [cyan]{workDir}[/cyan] is invalid. Please check the directory.\n"
        )
        sys.exit(1)
    defaultResultDir = pathDir / '2_Results'
    metadata_path = Path(_metadata_folder)
    resume = set_resume_value(args)

    console.print(Align.center(gradient_text(ASCII_LOGO, colors)))
    print()
    skip_folders(args)
    print()

    def patient_level_analysis():
        folder_count = get_folder_count(workDir, args)
        total_folders = folder_count
        failedPatientFolder:Path = defaultResultDir / 'failed_patient_analysis.log'
        folder_analyzed_successfully = 0
        current_patient:str = ''

        if folder_count == 0:
            notify_missing_folder(workDir, console)
            return

        try:
            for folder in workDir.iterdir():
                if folder.is_dir() and 'patient' in folder.name.lower() and (args.skip is None or folder.name not in args.skip):
                    current_patient = folder.name
                    console.print(f"[bold green]Running pipeline for[/bold green] [cyan]{folder.name}[/cyan]...")
                    console.print(Panel(metadata_caption(args), title="[bold yellow]Metadata[/bold yellow]", expand=False))
                    console.print(f"[bold magenta]Remaining folders to analyse:[/bold magenta] [white]{folder_count - 1}[/white]")
                    resultDir = defaultResultDir / f"Results_{folder.name}"
                    sampleMetadataPath = set_metadata_path(metadata_path, args.pathDir, args, resultDir)

                    result = subprocess.run([
                            'nextflow', '-c', confPath, 'run', metontiimeScript,
                            f'--workDir={folder}',
                            f'--resultsDir={resultDir}',
                            f'--sampleMetadata={sampleMetadataPath}',
                            '-profile', 'docker', f'{resume}'
                        ],stderr=subprocess.PIPE, text=True, check=True)
                    if result.returncode == 0:
                        folder_analyzed_successfully += 1

                    folder_count -= 1
                    if folder_analyzed_successfully == total_folders:
                        console.print("[bold green]✅ Done. All folders have been analyzed.[/bold green]")
                    else:
                        msg = f"""
                    ⚠️ Partially done. Some folders have been analyzed.

                    Folders analyzed successfully: [bold green]{folder_analyzed_successfully}[/bold green]
                    Folders failed:                 [bold red]{total_folders - folder_analyzed_successfully}[/bold red]
                    """
                        console.print(
                            Panel(
                                Align.center(msg.strip()),
                                border_style="yellow",
                                title="[bold yellow]RESULT WARNING[/bold yellow]"
                            )
                        )
        except subprocess.CalledProcessError as e:
            block = re.search(r"ERROR ~[\s\S]*?(?=\n\S|$)", e.stderr)
            if block:
                with open(failedPatientFolder, 'a') as failed_runs:
                        failed_runs.write(f"Analyse failed for {current_patient}:\n")
                        failed_runs.write("Nextflow error block:\n")
                        failed_runs.write(block.group().strip())
                        failed_runs.write('\n\n')
            else:
                with open(failedPatientFolder, 'a') as failed_runs:
                        failed_runs.write(f"Analyse failed for {current_patient}\n")
                        failed_runs.write("Error block:\n")
                        failed_runs.write(e.stderr)
                        failed_runs.write('\n\n')

        except FileNotFoundError:
            console_err.print(Panel(
                """[bold red][ERROR][/bold red] - 'nextflow' command not found. Is Nextflow installed?

        To install Nextflow, follow these steps:

        1. Install Java (Nextflow needs Java to run):
        - [bold]Linux/macOS[/bold]: Run `[bold cyan]sudo apt install openjdk-11-jdk[/bold cyan]` (Linux) or `[bold cyan]brew install openjdk@11[/bold cyan]` (macOS)
        - [bold]Windows[/bold]: Install WSL (Windows Subsystem for Linux), then follow the Linux steps

        2. Install Nextflow:
        - Run the command: `[bold cyan]curl -s https://get.nextflow.io | bash[/bold cyan]` or `[bold cyan]wget -qO- https://get.nextflow.io | bash[/bold cyan]`

        3. Make Nextflow accessible:
        - Move the `[bold cyan]nextflow[/bold cyan]` file to a directory in your PATH: `[bold cyan]mv nextflow /usr/local/bin/[/bold cyan]` (Linux/macOS)

        Once done, run `[bold cyan]nextflow -v[/bold cyan]` to check if it's installed correctly.
        """,
                border_style="red",
                title="[bold red]Nextflow Not Found[/bold red]"
            ))
            sys.exit(1)

        except KeyboardInterrupt:
            console.print("[bold yellow]⏹ Interrupted by user. Exiting...[/bold yellow]")



    def barcode_level_analysis():

        def try_restoration(tmp_dest: Path, parent: Path) -> None:
            """
            Attempt to restore `folder` from `tmp_dest` back to original location retrieved using `parent / tmp_dest.name`.

            Returns:
                If the restore fails, the function handles user notification and provides paths for manual intervention.
                No value is returned.
            """
            original_location = parent / tmp_dest.name
            try:
                shutil.move(tmp_dest, original_location)
                tmp_dest.parent.rmdir()


            except shutil.Error as e:
                message = Text()
                message.append("❌ Failed to restore folder\n\n", style="bold red")
                message.append("Folder: ", style="bold")
                message.append(f"{folder.name}\n", style="cyan")
                message.append("Original location: ", style="bold")
                message.append(f"{original_location}\n\n", style="cyan")

                message.append("Cause:\n", style="bold yellow")
                message.append(f"{e}\n\n", style="yellow")

                message.append("Manual action required:\n", style="bold")
                message.append("Please move the folder manually from ", style="white")
                message.append(f"{tmp_dest}", style="cyan")
                message.append(" back to ", style="white")
                message.append(f"{parent}", style="cyan")
                message.append(" but only if necessary.\n\n", style="red")
                message.append(
                    "We sincerely apologize for the inconvenience.",
                    style="dim",
                )

                console_err.print(
                    Panel(
                        message,
                        title="Restore Operation Failed",
                        border_style="red",
                    )
                )

            except Exception as e:
                message = Text()
                message.append("❌ Unexpected error while restoring folder\n\n", style="bold red")

                message.append("Folder: ", style="bold")
                message.append(f"{folder.name}\n", style="cyan")

                message.append("Original location: ", style="bold")
                message.append(f"{parent}\n", style="cyan")

                message.append("Temporary location: ", style="bold")
                message.append(f"{tmp_dest}\n\n", style="cyan")

                message.append("Cause:\n", style="bold yellow")
                message.append(f"{getattr(e, 'strerror', str(e))}\n\n", style="yellow")

                message.append("Manual recovery may be required.\n", style="white")
                message.append("Please verify the folder locations and move from ", style="white")
                message.append(f"{tmp_dest}", style="cyan")
                message.append(" back to ", style="white")
                message.append(f"{parent}", style="cyan")
                message.append(" but only if necessary.\n\n", style="red")
                message.append("We’re really sorry about that.", style="dim")

                console_err.print(
                    Panel(
                        message,
                        title="Unexpected Error",
                        border_style="red",
                    )
                )

        def try_move_to_tmp(folder: Path, tmp_dest: Path) -> _temporaryMoveState:
            """
            Attempt to move `folder` to temporary location `tmp_dest`.

            Returns:
                _temporaryMoveState: An object describing the outcome of the temporary move attempt, containing:
                    success (bool): True if the temporary move succeeded
                    failed (bool): True if the temporary move failed (computed as the opposite of success)
            Notes:
                If the move fails, the folder will be skipped from analysis
                because FASTQ concatenation cannot be performed. User can either:
                1. Relaunch analysis for that folder in a manually created tmp folder
                2. Relaunch analysis with a skip file containing all successfully analyzed folders
            """
            try:
                shutil.move(folder, tmp_dest)
                return _temporaryMoveState(success=True)

            except shutil.Error as e:
                message = Text()
                message.append("❌ Failed to move folder to temporary location\n\n", style="bold red")

                message.append("Folder: ", style="bold")
                message.append(f"{folder.name}\n", style="cyan")

                message.append("Intended temporary location: ", style="bold")
                message.append(f"{tmp_dest}\n\n", style="cyan")

                message.append("Cause:\n", style="bold yellow")
                message.append(f"{e}\n\n", style="yellow")

                message.append(
                    "Impact on analysis:\n",
                    style="bold white",
                )
                message.append(
                    "Since the folder could not be moved, FASTQ concatenation cannot be performed.\n"
                    "This folder will be skipped in the current analysis run.\n\n",
                    style="red",
                )

                message.append(
                    "Next steps:\n",
                    style="bold white",
                )
                message.append(
                    "1. Relaunch the analysis for this folder in a manually created tmp folder.\n"
                    "2. Relaunch the analysis using a skip file containing all successfully analyzed folders.\n",
                    style="white",
                )

                console_err.print(
                    Panel(
                        message,
                        title="Move to Temporary Failed - Folder Skipped",
                        border_style="red",
                    )
                )
                return _temporaryMoveState(success=False)

            except Exception as e:
                message = Text()
                message.append("❌ Unexpected error while moving folder to temporary location\n\n", style="bold red")

                message.append("Folder: ", style="bold")
                message.append(f"{folder.name}\n", style="cyan")

                message.append("Intended temporary location: ", style="bold")
                message.append(f"{tmp_dest}\n\n", style="cyan")

                message.append("Cause:\n", style="bold yellow")
                message.append(f"{getattr(e, 'strerror', str(e))}\n\n", style="yellow")

                message.append(
                    "Impact on analysis:\n",
                    style="bold white",
                )
                message.append(
                    "Since the folder could not be moved, FASTQ concatenation cannot be performed.\n"
                    "This folder will be skipped in the current analysis run.\n\n",
                    style="red",
                )

                message.append(
                    "Next steps:\n",
                    style="bold white",
                )
                message.append(
                    "1. Relaunch the analysis for this folder in a manually created tmp folder.\n"
                    "2. Relaunch the analysis using a skip file containing all successfully analyzed folders.\n",
                    style="white",
                )

                console_err.print(
                    Panel(
                        message,
                        title="Unexpected Error - Folder Skipped",
                        border_style="red",
                    )
                )
                return _temporaryMoveState(success=False)


        def ensure_concatenate_fastq(folder: Path, parent: Path, return_to_original: bool = False) -> Tuple[_temporaryMoveState, _workDir] | None :
            wDir = parent / f'temp-workDir-{folder.name}'
            tmp_dest = wDir / folder.name
            if return_to_original:
                return try_restoration(tmp_dest, parent)
            return try_move_to_tmp(folder, tmp_dest), wDir


        folder_count = get_folder_count(workDir, args)
        if folder_count == 0:
            notify_missing_folder(workDir, console, patient_level=False)
            return
        try:
            for folder in workDir.iterdir():
                if folder.is_dir() and 'barcode' in folder.name.lower() and (args.skip is None or folder.name not in args.skip):
                    console.print(f"[bold green]Running pipeline for[/bold green] [cyan]{folder.name}[/cyan]...")
                    console.print(f"[bold magenta]Remaining folders to analyse:[/bold magenta] [white]{folder_count - 1}[/white]")
                    resultDir = defaultResultDir / f"Results_{folder.name}"
                    sampleMetadataPath = set_metadata_path(metadata_path, args.pathDir, args, resultDir)
                    retval = ensure_concatenate_fastq(folder, workDir)
                    if retval:
                        move, workingDir = retval
                        if move.failed:
                            continue

                        subprocess.run([
                            'nextflow', '-c', confPath, 'run', metontiimeScript,
                            f'--workDir={workingDir}',
                            f'--resultsDir={resultDir}',
                            f'--sampleMetadata={sampleMetadataPath}',
                            '-profile', 'docker', f'{resume}'
                        ])
                        ensure_concatenate_fastq(folder, workDir, return_to_original=True)
                    folder_count -= 1
                    if folder_count == 0:
                        console.print("[bold green]✅ Done. All folders have been analyzed.[/bold green]")
        except FileNotFoundError:
            if 'folder' in locals():
                ensure_concatenate_fastq(folder, workDir, return_to_original=True) #type: ignore
            console_err.print(Panel(
                """[bold red][ERROR][/bold red] - 'nextflow' command not found. Is Nextflow installed?

        To install Nextflow, follow these steps:

        1. Install Java (Nextflow needs Java to run):
           - [bold]Linux/macOS[/bold]: Run `[bold cyan]sudo apt install openjdk-11-jdk[/bold cyan]` (Linux) or `[bold cyan]brew install openjdk@11[/bold cyan]` (macOS)
           - [bold]Windows[/bold]: Install WSL (Windows Subsystem for Linux), then follow the Linux steps

        2. Install Nextflow:
           - Run the command: `[bold cyan]curl -s https://get.nextflow.io | bash[/bold cyan]` or `[bold cyan]wget -qO- https://get.nextflow.io | bash[/bold cyan]`

        3. Make Nextflow accessible:
           - Move the `[bold cyan]nextflow[/bold cyan]` file to a directory in your PATH: `[bold cyan]mv nextflow /usr/local/bin/[/bold cyan]` (Linux/macOS)

        Once done, run `[bold cyan]nextflow -v[/bold cyan]` to check if it's installed correctly.
        """,
                border_style="red",
                title="[bold red]Nextflow Not Found[/bold red]"
            ))
            sys.exit(1)

        except KeyboardInterrupt:
            if 'folder' in locals():
                ensure_concatenate_fastq(folder, workDir, return_to_original=True) #type: ignore
            console.print("[bold yellow]⏹ Interrupted by user. Exiting...[/bold yellow]")


    if args.level == PATIENT_LEVEL:
        patient_level_analysis()
    elif args.level == BARCODE_LEVEL:
        barcode_level_analysis()
    else:
        console_err.print(
            "[bold red]✖ ERROR[/bold red] — Something went wrong.\n"
            "[dim]Are you sure you didn’t modify the source code?[/dim]"
        )
        sys.exit(1)


if __name__ == '__main__':
    automate_analysis()
