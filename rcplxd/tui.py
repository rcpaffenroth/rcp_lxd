"""Textual TUI forms for rcp_lxd subcommands.

The CLI works exactly as before. When a subcommand is given --interactive, it
pops up a small Textual form pre-filled with the current option values (whatever
defaults or flags came from the command line). The form returns a dict of edited
values, which the command then uses as if they'd been typed on the command line.
Cancelling (Esc) returns None so the command can abort cleanly.
"""

from dataclasses import dataclass
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, Switch


@dataclass
class Field:
    """One editable option in a form.

    kind is one of "text", "int", or "bool"; it decides which widget is shown
    and how the returned value is parsed.
    """

    key: str
    label: str
    kind: str = "text"
    default: Any = ""


class FormApp(App):
    """A one-screen form: one labelled widget per field, plus Submit/Cancel."""

    CSS = """
    VerticalScroll { padding: 1 2; }
    Label { margin-top: 1; color: $text-muted; }
    Input { width: 60; }
    #buttons { margin-top: 2; height: auto; }
    Button { margin-right: 2; }
    """

    BINDINGS = [
        ("ctrl+s", "submit", "Submit"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, title: str, fields: list[Field]) -> None:
        super().__init__()
        self.title = title
        self._fields = fields

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            for f in self._fields:
                yield Label(f.label)
                if f.kind == "bool":
                    yield Switch(value=bool(f.default), id=f"f_{f.key}")
                else:
                    # Textual's "integer" input type rejects non-numeric keystrokes.
                    input_type = "integer" if f.kind == "int" else "text"
                    yield Input(value=str(f.default), type=input_type, id=f"f_{f.key}")
            with Horizontal(id="buttons"):
                yield Button("Submit", variant="success", id="submit")
                yield Button("Cancel", variant="error", id="cancel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.action_submit()
        else:
            self.action_cancel()

    def action_submit(self) -> None:
        result: dict[str, Any] = {}
        for f in self._fields:
            widget = self.query_one(f"#f_{f.key}")
            if f.kind == "bool":
                result[f.key] = widget.value
            elif f.kind == "int":
                result[f.key] = int(widget.value or 0)
            else:
                result[f.key] = widget.value
        self.exit(result)

    def action_cancel(self) -> None:
        self.exit(None)


def run_form(title: str, fields: list[Field]) -> dict[str, Any] | None:
    """Run a form and return the edited values, or None if cancelled."""
    return FormApp(title, fields).run()
