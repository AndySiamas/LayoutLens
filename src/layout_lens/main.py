from __future__ import annotations

import typer
from rich.console import Console

from layout_lens.core.application import Application
from layout_lens.core.settings import Settings


app: typer.Typer = typer.Typer(add_completion=False)

@app.callback(invoke_without_command=True)
def cli(
    prompt: str | None = typer.Option(
        default=None,
        help="Natural-language prompt (if omitted, you will be asked interactively).",
    )
) -> None:
    typer.echo("LayoutLens — an agentic prompt to 3d interior design visualizer")

    user_prompt: str
    if prompt is not None and prompt.strip() != "":
        user_prompt = prompt.strip()
    else:
        user_prompt = typer.prompt("Enter your design prompt").strip()

    try:
        completion_message: str = ''
        console: Console = Console()
        with console.status("Working..."):
            settings: Settings = Settings()
            application: Application = Application(settings=settings)
            completion_message = application.run(user_prompt=user_prompt)

        typer.secho(completion_message, fg=typer.colors.GREEN)

    except Exception as exception:
        typer.secho("Something went wrong.", fg=typer.colors.RED, err=True)
        typer.echo(str(exception), err=True)
        raise typer.Exit(code=1)


def main() -> None:
    app()