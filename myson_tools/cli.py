# !/usr/bin/env python3
from typing import Callable
from rich.progress import Progress, SpinnerColumn, TextColumn
from myson_tools.utils import get_conda_env_path, get_metontiime_conf_file_path
from myson_tools.command.launch_metontiime import BARCODE_LEVEL, PATIENT_LEVEL
from rich.console import Console
from rich.prompt import Prompt
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
from rich import box
import subprocess
import signal
import sys
import os
from dotenv import load_dotenv

load_dotenv()
env = os.environ.copy()
env["PYTHONUTF8"] = "1"

console = Console()

colors = [
    "#66CCFF",
    "#9966CC",
    "#FF99CC"
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

ASCII_ART = """

███╗   ███╗██╗   ██╗███████╗ ██████╗ ███╗   ██╗   ████████╗ ██████╗  ██████╗ ██╗     ███████╗
████╗ ████║╚██╗ ██╔╝██╔════╝██╔═══██╗████╗  ██║   ╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██╔════╝
██╔████╔██║ ╚████╔╝ ███████╗██║   ██║██╔██╗ ██║█████╗██║   ██║   ██║██║   ██║██║     ███████╗
██║╚██╔╝██║  ╚██╔╝  ╚════██║██║   ██║██║╚██╗██║╚════╝██║   ██║   ██║██║   ██║██║     ╚════██║
██║ ╚═╝ ██║   ██║   ███████║╚██████╔╝██║ ╚████║      ██║   ╚██████╔╝╚██████╔╝███████╗███████║
╚═╝     ╚═╝   ╚═╝   ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝      ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚══════╝

                            A set of bio-tools easy to use
                                Copyright : Myson Dio
"""

def graceful_exit(signal, frame):
    console.print("\n👋 [bold red]Exiting... Have a nice day![/bold red]")
    sys.exit(0)

def display_menu():
    menu_text = Text()
    menu_text.append("\nSelect an option:\n\n", style="bold underline")
    options = [
        "1.  Rename barcode folders",
        "2.  Create patient folders",
        "3.  Move patient folders",
        "4.  Launch MetONTIIME pipeline (Patient - Level)",
        "5.  Launch MetONTIIME pipeline (Barcode - Level)",
        "6.  Separate metadata",
        "7.  Generate skip list (patients to exclude)",
        "8.  Merge tables",
        "9.  Get QZA tables and taxonomy",
        "10. Get feature tables",
        "11. Alpha diversity analysis",
        "12. Help",
        "13. Exit"
    ]
    for option in options:
        menu_text.append(f"{option}\n", style="bold cyan")
    panel = Panel(Align.center(menu_text), title="[bold magenta]Main Menu[/]", border_style="magenta", padding=(1, 2), box=box.DOUBLE_EDGE)
    console.print(panel)

help_texts = {
    "1" : "Rename barcode folders: This tool allows you to rename bacteria sample folders based on the information provided in an Excel file. You can specify the Excel file, the folder containing the samples, and/or a configuration file. Useful for standardizing folder names before downstream analysis.",
    "2" : "Create patient folders: Automatically creates patient-specific folders using data from an Excel file. You can provide the Excel file, the base folder, and/or a configuration file. This helps organize your data for each patient in a structured way.",
    "3" : "Move patient folders: Sorts and moves sample files into their respective patient folders based on Excel data. You can specify the Excel file, the folder, and/or a configuration file. Ensures that all samples are correctly grouped for each patient.",
    "4" : "Launch MetONTIIME pipeline: Runs the MetONTIIME bioinformatics pipeline for all patient folders in a given directory. Requires the main data directory (pathDir), and optionally the working directory, metadata file, resume flag, and skip list. Automates multi-sample analysis workflows.",
    "5" : "Launch MetONTIIME pipeline: Runs the MetONTIIME bioinformatics pipeline for all barcode folders in a given patient directory. Requires the main data directory (pathDir), and optionally the working directory. Automates multi-sample analysis workflows for failed runs.",
    "6" : "Separate metadata: Generates a metadata.tsv file for your samples, based on the folder structure and an Excel file. Requires the folder path and optionally allows force-overwriting existing files. Ensures your metadata is ready for downstream tools.",
    "7" : "Generate skip list: Scans a directory and generates a skip list file containing the names of all subfolders. Requires the path to the directory. Useful for excluding certain folders from batch analyses or pipelines.",
    "8" : "Merge tables: Combines multiple data tables (e.g., feature tables, metadata) into a single unified table. Useful for aggregating results from different runs or experiments into one file for easier comparison and downstream analysis. Runs inside the QIIME2 conda environment.",
    "9" : "Get QZA tables and taxonomy: Extracts QIIME2 artifact (QZA) tables and taxonomy assignments from your analysis results. This helps you retrieve processed data and taxonomic classifications for further exploration or reporting.",
    "10": "Get feature table: Extracts TSV feature tables by level and frequency from your analysis results (located in the collapseTables folder), specifically the absolute frequency (absfreq) and relative frequency (relfreq) for levels 4 through 7.",
    "11": "Alpha diversity analysis: Calculates alpha diversity metrics (Shannon, Simpson, richness, evenness) from a feature table and metadata. Prompts for a TSV feature table, Excel metadata file, and optional output file. Outputs a merged CSV with all metrics and metadata for each sample.",
    "12": "Help: Show this help panel with detailed descriptions for each menu option.",
    "13": "Exit: Quit the program and return to your shell. Use this option when you are done with your session.",
}

def display_help_panel():
    help_panel_text = Text()
    help_panel_text.append("\nHelp for Options:\n\n", style="bold underline")
    for key in sorted(help_texts, key=lambda x: int(x)):
        desc = help_texts[key]
        help_panel_text.append(f"{key}. {desc}\n\n", style="bold green")
    panel = Panel(Align.center(help_panel_text), title="[bold yellow]Help Panel[/]", border_style="yellow", padding=(1, 2))
    console.print(panel)


def run_subprocess_with_spinner(command_args, env=env, description="Running subprocess..."):
    """
    Run a subprocess command with a rich spinner and clean output formatting.

    Args:
        command_args (list): Command and arguments to run.
        env (dict, optional): Environment variables.
        description (str): Message to show beside the spinner.
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            task = progress.add_task(f"[cyan]{description}", total=None)
            proc = subprocess.Popen(
                command_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=False,
                env=env
            )
            stdout, stderr = proc.communicate()
            progress.remove_task(task)

            if proc.returncode == 0:
                console.print("[bold green]✔ Task completed successfully![/]")
                if stdout.strip():
                    console.print("[bold white]Output:[/]")
                    console.print(stdout)
            else:
                console.print(f"[bold red]✘ Task failed with exit code {proc.returncode}[/]")

                if stderr.strip():
                    console.print(f"[bold red]\n{stderr}[/]")

                if stdout.strip():
                    for line in stdout.splitlines():
                        if any(keyword in line.lower() for keyword in ["❌", "Error", "Exception"]):
                            console.print(f"[bold red]{line}[/]")
                        else:
                            console.print(Align.center(line))

                if not stderr.strip() and not stdout.strip():
                    console.print("[bold red]No output received from subprocess.[/]")

    except Exception as e:
        console.print(f"[bold red]❌ Exception occurred while running subprocess: {e}[/]")
       

def reset_terminal():
    """Resets terminal settings even after subprocess terminal corruption."""
    try:
        subprocess.run(
            ['stty', 'sane'],
            stdin=open('/dev/tty'),
            stdout=open('/dev/tty', 'w'),
            stderr=subprocess.DEVNULL
        )
        print("\033[?25h", end="") 
    except Exception as e:
        console.print(f"\n[bold red]Warning: Terminal may still be corrupted ({e})[/]")
        console.print("[bold cyan]Tip: Manually type `reset` and press Enter if needed.[/]")

def run_subprocess_clean(command_args, env=env):
    try:
        proc = subprocess.Popen(
            command_args,
            shell=False,
            env=env,
        )
        proc.wait()

        if proc.returncode == 0:
            console.print("[bold green]✔ Task completed successfully![/]")
        else:
            console.print(f"[bold red]✘ Task failed with exit code {proc.returncode}[/]")
            

    except KeyboardInterrupt:
        console.print("\n[bold yellow]⏹ Interrupted by user (Ctrl+C)[/]")
        try:
            proc.terminate() # type: ignore
            proc.wait(timeout=3) # type: ignore
        except Exception:
            proc.kill() # type: ignore
        finally:
            reset_terminal()
            console.print("[bold yellow]Terminal reset. You can type again.[/]")



def prompt_for_path(prompt_text, default=None, optional=False):
    while True:
        val = Prompt.ask(f"[bold white]{prompt_text}[/]" + (f" (default: {default})" if default else ""), default=default or "")
        if val or optional:
            return val if val else default
        else:
            console.print("[bold red]This field is required.[/]")
            
def run_python_tool(module: str, args: list | None = None, description: str = "Running module...", subprocess_fn: Callable[[list[str]], None] | None = None) -> None:
    """
    Run a Python tool via -m module.

    Args:
    -------------------
        module (str) : the module to be ran path
        args (list, optional) : a list of arguments that'll be used as cli args
        description (str) : the description that'll when the tool will be running 
        subprocess_fn(Callable(list[str]) -> None) : mainly to allow the use of subprocess_clean
    """
    
    cmd = [sys.executable, '-m', module]
    if args:
        cmd += args
    if subprocess_fn:
        subprocess_fn(cmd)
    else:
        run_subprocess_with_spinner(cmd, description=description)
    

def main():
    signal.signal(signal.SIGINT, graceful_exit)
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
    console.print(Align.center(gradient_text(ASCII_ART, colors)))
    while True:
        display_menu()
        choice = Prompt.ask("[bold white]Enter your choice[/]", choices=[str(i) for i in range(1, 14)])
        if choice == '13':
            console.print("[bold red]👋 Goodbye![/bold red] [dim]See you next time![/dim]")
            break
        elif choice == '12':
            display_help_panel()
            continue
        elif choice == '11':
            # Alpha diversity analysis
            feature_table = prompt_for_path("Enter the path to the TSV feature table file")
            metadata = prompt_for_path("Enter the path to the Excel metadata file")
            output_file = prompt_for_path("Enter the output directory. Output filename will be <feature_table_basename>_alpha_diversity_merged.csv")

            args = ["-f", feature_table, "-m", metadata, "-o", output_file]
            
            run_python_tool(
                module="myson_tools.command.alpha_div_analysis",
                args=args,
                description="Running alpha diversity analysis..."
            )
            continue
        elif choice == '10':
            # Get Feature tables
            folder = prompt_for_path("Enter the path to the '2_Result' folder for TSV extraction")
            output_dir = prompt_for_path("Enter an output directory for the frequency_level folders")
    
            args = ["--folder", folder, "--output", output_dir]
            run_python_tool(
                module="myson_tools.command.get_feature_table",
                args=args,
                description="Extracting TSV feature tables..."
            )
            continue
        elif choice == '9':
            # Get QZA tables and taxonomy
            
            folder = prompt_for_path("Enter the path to the '2_Result' folder for QZA extraction")
            output_dir = prompt_for_path("Enter an output directory for the frequency_level folders")
        
            args = ["--folder", folder, "--output", output_dir]
            run_python_tool(
                module='myson_tools.command.get_qza_tables_and_taxonomy',
                args=args,
                description="Extracting QZA tables and taxonomy..."
            )
            continue
        elif choice == '8':
            # Merge QZA tables using selected conda env
            chosen_env = get_conda_env_path()
            if chosen_env is None:
                continue

            dir_path = prompt_for_path("Enter the directory containing QZA tables to merge")
            out_path = prompt_for_path("Enter the directory to output the merged tables (if it doesn't exist, it will be created)")
            script_path = str(Path(__file__).parent /"scripts" / "merge_tables.sh")

            cmd = ["conda", "run", "-n", chosen_env, "bash", script_path, dir_path, out_path]

            run_subprocess_with_spinner(cmd, description=f"Merging QZA tables in environment: {chosen_env}...")
            continue
        elif choice == '1':
            # Rename barcode folders
            config = prompt_for_path("Config file path (optional)", optional=True)
            excel = prompt_for_path("Excel file path (leave blank to use config)", optional=True)
            folder = prompt_for_path("Folder path (leave blank to use config)", optional=True)
            args = []
            if config:
                args += ['-c', config]
            if excel:
                args += ['-e', excel]
            if folder:
                args += ['-f', folder]
            
            run_python_tool(
                module="myson_tools.command.cli_barcode_folder_renamer",
                args=args,
                description="🧬 Renaming barcode folders..."
            )
            continue
        elif choice == '2':
            # Create patient folders
            config = prompt_for_path("Config file path (optional)", optional=True)
            excel = prompt_for_path("Excel file path (leave blank to use config)", optional=True)
            folder = prompt_for_path("Folder path (leave blank to use config)", optional=True)
            args = []
            if config:
                args += ['-c', config]
            if excel:
                args += ['-e', excel]
            if folder:
                args += ['-f', folder]
            args.append("--create-folders")
            
            run_python_tool(
                module="myson_tools.command.cli_patient_folder_manager",
                args=args,
                description="📁 Creating patient folders..."
            )
            continue
        elif choice == '3':
            # Move patient folders (sort-samples)
            config = prompt_for_path("Config file path (optional)", optional=True)
            excel = prompt_for_path("Excel file path (leave blank to use config)", optional=True)
            folder = prompt_for_path("Folder path (leave blank to use config)", optional=True)
            args = []
            if config:
                args += ['-c', config]
            if excel:
                args += ['-e', excel]
            if folder:
                args += ['-f', folder]
            args.append("--sort-samples")
            
            run_python_tool(
                module="myson_tools.command.cli_patient_folder_manager",
                args=args,
                description="📦 Moving and sorting patient folders..."
            )
            continue
        elif choice == '4':
            # Launch MetONTIIME pipeline (Patient - Level)
            pathDir = prompt_for_path("PathDir (required)")
            workDir = prompt_for_path("WorkDir", default="1_Raw_data/fastq_pass", optional=True)
            # conf = get_metontiime_conf_file_path()
            # if not conf: 
            #     continue
            conf=''
            metadata = prompt_for_path("Metadata (optional, leave blank for default)", optional=True)
            resume = Prompt.ask("Resume?", choices=["yes", "no"], default="no")
            skip = prompt_for_path("Skip (space-separated list or @path/to/skip-list.txt, optional)", optional=True)
            args = ['-p', pathDir, '--level', PATIENT_LEVEL]
            if workDir:
                args += ['-w', workDir]
            args += ['-c', conf]
            if metadata:
                args += ['-m', metadata]
            if resume == "yes":
                args += ['--resume']
            if skip:
                args += ['--skip'] + skip.split()
            
            run_python_tool(
                module="myson_tools.command.launch_metontiime",
                args=args,
                subprocess_fn=run_subprocess_clean
            )
            continue
        elif choice == '5':
            # Launch MetONTIIME pipeline (Barcode - Level)
            pathDir = prompt_for_path("PathDir (required)")
            workDir = prompt_for_path("WorkDir", default="1_Raw_data/fastq_pass", optional=True)
            # conf = get_metontiime_conf_file_path()
            # if not conf: 
            #     continue
            conf=''
            skip = prompt_for_path("Skip (space-separated list or @path/to/skip-list.txt, optional)", optional=True)
            args = ['-p', pathDir, '-c', conf, '--level', BARCODE_LEVEL]
            if workDir:
                args += ['-w', workDir]
            if skip:
                args += ['--skip'] + skip.split()
                
            run_python_tool(
                module="myson_tools.command.launch_metontiime",
                args=args,
                subprocess_fn=run_subprocess_clean
            )
            continue
        elif choice == '6':
            # Separate metadata
            folder_path = prompt_for_path("Folder path (--folder-path, required)")
            force = Prompt.ask("Force overwrite if exists?", choices=["yes", "no"], default="no")
            args = ['-p', folder_path]
            if force == "yes":
                args.append('--force')
            
            run_python_tool(
                module="myson_tools.command.separate_metadata",
                args=args,
                description="🧾 Separating metadata files..."
            )
            continue
        elif choice == '7':
            # Generate skip list
            path_dir = prompt_for_path("Path to run directory (ex: 241126_ICMc..etc)")
            output_dir = prompt_for_path("Enter an output directory for the skip_list.txt")
            args = ['--path-dir', path_dir, '--output', output_dir]
            
            run_python_tool(
                module="myson_tools.command.generate_skip_list", 
                args=args, 
                description="🛑 Generating skip list of samples to exclude..."
            )
            continue
        else:
            console.print("❌ [bold red]Invalid choice[/bold red]! Please select a valid option.")

if __name__ == "__main__":
    main()
