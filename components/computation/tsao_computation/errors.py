class TsaoError(Exception):
    """Base exception with user-actionable context."""


class ContractError(TsaoError):
    pass


class StateTransitionError(TsaoError):
    pass


class SecurityError(TsaoError):
    pass


class ValidationError(TsaoError):
    pass
