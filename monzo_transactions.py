"""Module defining the class to interact with Monzo transactions."""


class MonzoTransactions:
    """Class to interact with Monzo transactions."""

    def __init__(self, spreadsheet_id: str, sheet_name: str, range: tuple[str, str]):
        self.spreadsheet_id: str = spreadsheet_id
        self.sheet_name: str = sheet_name
        self.range: tuple[str, str] = range

    @property
    def range_name(self) -> str:
        return f"{self.sheet_name}!{self.range[0]}:{self.range[1]}"
