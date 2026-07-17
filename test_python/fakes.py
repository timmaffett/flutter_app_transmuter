"""Tiny stand-ins for googleapiclient request/resource objects."""


class FakeRequest:
    def __init__(self, result):
        self._result = result

    def execute(self):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakeResource:
    """Chainable fake for googleapiclient resources.

    Keyword values that are callables become methods whose result is wrapped in a
    FakeRequest (so .execute() works); non-callables (e.g. nested FakeResources)
    become zero-arg methods returning the value itself, which is how resource
    chaining like firebase.projects().androidApps().sha() is modeled.
    """

    def __init__(self, **members):
        for name, value in members.items():
            if callable(value) and not isinstance(value, FakeResource):
                setattr(self, name, self._wrap(value))
            else:
                setattr(self, name, lambda v=value: v)

    @staticmethod
    def _wrap(fn):
        def method(*args, **kwargs):
            result = fn(*args, **kwargs)
            return result if isinstance(result, FakeRequest) else FakeRequest(result)
        return method
