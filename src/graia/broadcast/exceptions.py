class OutOfMaxGenerater(Exception):
    pass


class InvalidDispatcher(Exception):
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


class InvalidEventName(Exception):
    pass


class InvalidContextTarget(Exception):
    pass


class PropagationCancelled(Exception):
    pass


class ExecutionStop(Exception):
    pass
