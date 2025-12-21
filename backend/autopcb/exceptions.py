import json

class MissingSchematicSymbolException(Exception):
    """Custom exception thrown when chip was not found in the library"""

    def __init__(self, chip_id: str):
        self.chip_id = chip_id
        super().__init__(f"Schematic symbol for a chip with ID: {chip_id} is not in the library")


class MissingBomInfoException(Exception):
    """Exception thrown when a chip was used that has insufficient info for the bill of materials"""

    def __init__(self, chip_id: str):
        self.chip_id = chip_id
        super().__init__(f"Schematic symbol: {chip_id} does not have sufficient bill of materials information.")


class SubcircuitCodeError(Exception):
    """Custom exception for handling syntax errors in subcircuits."""

    def __init__(self, lineno: int):
        super().__init__(json.dumps(lineno))
        self.lineno = lineno


class UserFeedback(Exception):
    """Throws an error that stems from wrong user input, not software bug"""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)