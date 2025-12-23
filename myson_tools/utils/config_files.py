import os
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from .io_utils import env_var_missing


def get_metontiime_conf_file_path() -> str | None:
    """
    Warning
    ----------
    This Module is unused
    ----------
    Displays a rich-styled prompt to Choose a conf file,
    and lists all available MetONTIIME conf file.
    """
    console = Console()
    console_err = Console(stderr=True)
    _conf_path=os.getenv('CONF_PATH')
    print(os.getenv('CONF_PATH'))
    if _conf_path is None:
        env_var_missing(
            var_name='CONF_PATH',
            err_stream=console_err
        )
    conf_path:Path = Path(_conf_path)
    conf_files: dict[int, str] = {}
    conf_idx:int = 1

    selection_text = Text()
    selection_text.append("\nChoose the reference configuration file for your analysis:\n", style="bold green")
    selection_text.append("→ Select from the list of existing configuration files below\n", style="bold yellow")

    prompt_panel = Panel(
        selection_text,
        title="🧬 Configuration Selection",
        border_style="bright_green",
        box=box.DOUBLE,
        padding=(1, 2)
    )

    def show_error(message: str, title: str = "❌ Configuration Error"):
        """Display a modern error panel with optional title."""
        console_err.print(
            Panel(
                Text.from_markup(f"Error loading configuration files\nCause: {message}", style="bold red"),
                border_style="red",
                title=title,
                title_align="left"
            )
        )

    try:
        for conf in conf_path.iterdir():
            if conf.is_file() and conf.name.endswith(".conf"):
                conf_files[conf_idx] = conf.name
                conf_idx += 1
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as e:
            messages = {
                FileNotFoundError: f"Directory not found: [cyan]{conf_path}[/cyan]. Please check the path.",
                NotADirectoryError: f"Not a directory: [cyan]{conf_path}[/cyan].",
                PermissionError: f"No permission to access: [cyan]{conf_path}[/cyan].",
                OSError: f"OS error: {e}"
            }
            show_error(messages.get(type(e), str(e)))
            return

    panel_lines = []
    for idx, conf_name in conf_files.items():
        panel_lines.append(f"[bold cyan]{idx}.[/] {conf_name}")

    panel_text = "\n".join(panel_lines)

    conf_panel = Panel(
        panel_text,
        title="[bold green]Available Configuration Files[/bold green]",
        border_style="cyan",
        box=box.ROUNDED
    )

    console.print(prompt_panel)
    console.print(conf_panel)
    choice = Prompt.ask(
        "[bold white]Select the configuration file to use[/bold white] 🔹",
        choices=[str(i) for i in range(1, conf_idx)],
        show_choices=True
    )
    chosen_conf = conf_files.get(int(choice))
    console.print(
        "🚀 [bold green]Launching pipeline with configuration:[/bold green] "
        f"[cyan]{chosen_conf}[/cyan] ⚡",
        justify="left"
    )

    return chosen_conf
