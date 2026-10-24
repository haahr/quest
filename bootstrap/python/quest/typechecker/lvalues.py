"""L-Value and Reference Parameter Validation."""

from __future__ import annotations

from quest.diagnostics import QuestTypeError
from quest.types.env import Environment
from quest.types import QOutType, QType, QVarType, is_subtype


def check_lvalue_mode_type(
    param_type: QType,
    dest_raw_type: QType,
    is_out: bool,
    target_desc: str,
    offset: int,
    env: Environment,
) -> QType:
    """Unwraps reference cell types and validates invariance (var) or covariance (out)."""
    dest_type = (
        dest_raw_type.element_type
        if isinstance(dest_raw_type, (QVarType, QOutType))
        else dest_raw_type
    )
    if is_out:
        if not is_subtype(param_type, dest_type, env):
            raise QuestTypeError(
                f"Type mismatch on out parameter: parameter type '{param_type}' is not a subtype "
                f"of destination {target_desc} type '{dest_type}'",
                offset=offset,
            )
    else:
        if not (
            is_subtype(param_type, dest_type, env)
            and is_subtype(dest_type, param_type, env)
        ):
            raise QuestTypeError(
                f"Type mismatch on var parameter: expected exactly '{param_type}', but got "
                f"{target_desc} of type '{dest_type}' (var parameters are invariant)",
                offset=offset,
            )
    return dest_type
