from dataclasses import dataclass, field

from model.position import Position

_KIND_MAP = {
    "R": "rook",
    "B": "bishop",
    "Q": "queen",
    "N": "knight",
    "K": "king",
    "P": "pawn",
}

_SYMBOL_MAP = {value: key for key, value in _KIND_MAP.items()}
_VALID_STATES = {"idle", "moving", "captured"}


@dataclass(unsafe_hash=True)
class Piece:
    color: str
    kind: str
    cell: Position
    state: str = "idle"
    id: str = field(default="")

    def __post_init__(self):
        if self.color not in ("w", "b"):
            raise ValueError(f"Invalid piece color: {self.color}")
        if self.kind not in _SYMBOL_MAP:
            raise ValueError(f"Invalid piece kind: {self.kind}")
        if self.state not in _VALID_STATES:
            raise ValueError(f"Invalid piece state: {self.state}")
        if not self.id:
            object.__setattr__(self, "id", f"{self.color}{self.symbol}@{self.cell.row},{self.cell.col}")

    @property
    def symbol(self) -> str:
        return _SYMBOL_MAP[self.kind]

    @property
    def token(self) -> str:
        return f"{self.color}{self.symbol}"

    @classmethod
    def from_token(cls, token: str, cell: Position, state: str = "idle") -> "Piece":
        if len(token) != 2 or token[0] not in ("w", "b") or token[1] not in _KIND_MAP:
            raise ValueError(f"Invalid piece token: {token}")
        kind = _KIND_MAP[token[1]]
        return cls(color=token[0], kind=kind, cell=cell, state=state, id=f"{token}@{cell.row},{cell.col}")
