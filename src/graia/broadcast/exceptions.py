class OutOfMaxGenerater(Exception):
    pass


class InvaildDispatcher(Exception):
    pass


class RequirementCrashed(Exception):
    pass


class DisabledNamespace(Exception):
    pass


class ExistedNamespace(Exception):
    pass


class UnexistedNamespace(Exception):
    pass


class RegisteredEventListener(Exception):
    pass


class InvaildEventName(Exception):
    pass


class InvaildContextTarget(Exception):
    pass


class PropagationCancelled(Exception):
    pass


class ExecutionStop(Exception):
    pass
