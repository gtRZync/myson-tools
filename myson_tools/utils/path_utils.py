from pathlib import Path
import re

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def normalize_id_with_text(val: str, reference: dict, is_patient:bool) -> str:
    val = val.strip().replace('\u00A0', ' ') #removing nbsp to be able to split, it's not always there but it's safer
    parts = val.split(' ', 1)
    base = parts[0]
    tail = parts[1] if len(parts) > 1 else ''

    for key, mapped in reference.items():
        if base == key or base.startswith(key):
            base = mapped
            break

    return base + (f"-{tail}" if tail else "") if not is_patient else base + (f"_{tail}" if tail else "")


def get_barcode_value(name: str) -> int:
    match = re.search(r'\d+', name)
    return int(match.group()) if match else -1



def notify_missing_folder(workDir: Path, stream: Console, patient_level: bool = True):
    """
    Notify the user that a folder was not found in the work directory.

    Parameters:
    - workDir (str): The path to the working directory.
    - patient_level (bool): True for patient-level folder, False for barcode-level folder.
    """
    missing_folder = "patient folder" if patient_level else "barcode folder" 
    folder_name = "PATIENT-LEVEL analysis" if patient_level else "BARCODE-LEVEL analysis"
    alt_folder_name = "BARCODE-LEVEL analysis" if patient_level else "PATIENT-LEVEL analysis"

    message = Text()
    message.append(f"⚠️  No {missing_folder} was found in the working directory:\n", style="bold red")
    message.append(f"   {workDir}\n\n", style="bright_yellow")
    message.append("Please check the path, or if you did not mean to use the ", style="white")
    message.append(folder_name, style="bold magenta")
    message.append(", consider using the ", style="white")
    message.append(alt_folder_name, style="bold green")
    message.append(" instead.", style="white")

    panel = Panel(
        message,
        title="[bold yellow]Warning[/bold yellow]",
        border_style="bright_yellow",
        expand=False
    )

    stream.print(panel)


# Example usage:
# notify_missing_folder("/path/to/workdir")         # Patient-level by default
# notify_missing_folder("/path/to/workdir", False) # Barcode-level
