from rich.console import Console, RenderableType
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
from rich import box
import subprocess


def get_conda_env_path() -> Path | None:
    """
    Brief
    -------------
    Displays a rich-styled prompt to activate a Conda environment,
    and lists all available Conda environments using subprocess.

    Returns
    --------------
    The chosen conda env's path
    """
    
    def show_output(renderable: RenderableType) -> None:
        envs_panel = Panel(
            renderable,
            title="📦 Conda Environments",
            border_style="cyan",
            box=box.ROUNDED
        )
        console.print(envs_panel)
    
    console = Console()

    activation_text = Text()
    activation_text.append("\n  Activate your Conda environment:\n", style="bold green")
    activation_text.append("\n  $ chose from the list of existing environment\n", style="bold yellow")

    prompt_panel = Panel(
        activation_text,
        title="🐍 Conda Activation",
        border_style="green",
        box=box.DOUBLE
    )

    try:
        result = subprocess.run(
            ["conda", "info", "--envs"],
            capture_output=True,
            text=True,
            check=True,
            shell=False
        )
        envs_output = result.stdout
        typical_envs_info_return = [' ', '*', '#', 'active', '->', 'conda', 'environments:', 'base', '+', 'frozen']
        envs = [string for string in str(envs_output).split() if string not in typical_envs_info_return]
        
        choices = "\n".join([f"[bold cyan]{idx+1}.[/] [bold white]{Path(env).name}[/]" for idx, env in enumerate(envs)]) 
        
        console.print(prompt_panel)
        show_output(choices)
        chosen_env = Prompt.ask("[bold white]Enter the number of the conda env you wish to activate[/]", choices=[str(i) for i in range(1, len(envs)+1)]) 
        return Path(envs[int(chosen_env) - 1]) 
    except subprocess.CalledProcessError as e:
        envs_output = f"[Error] Failed to fetch environments:\n{e.stderr}"
        show_output(envs_output)
        return None
    except FileNotFoundError:
        envs_output = """
                        [bold red]\n[ERROR] - 'conda' command not found. Is Conda installed?[/]
                        To install Conda, follow these steps:

                        1. Download and install Miniconda (minimal installer):
                        - Go to: [link=https://docs.conda.io/en/latest/miniconda.html][bold][underline]https://docs.conda.io/en/latest/miniconda.html[/underline][/bold][/link]
                        - Choose the installer for your OS ([code]Windows[/code], [code]macOS[/code], [code]Linux[/code]).

                        2. Run the installer:
                        - [bold]Windows[/]: Double-click the [code].exe[/code] file.
                        - [bold]macOS/Linux[/]: Run the [code].pkg[/code] or [code].sh[/code] installer in the terminal.

                        3. Verify installation:
                        - Run: [code]conda --version[/code] to confirm Conda is installed.
                        """
        show_output(envs_output)
        return None

if __name__ == '__main__':
    path = get_conda_env_path()