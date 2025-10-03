"""
Context proxy for seamless access to current context objects.
"""
from typing import Any, Iterator
from .paragon import _PARAGON


class _ContextProxy:
    """Proxy that delegated to current context object with full magic method support."""
    def __init__(self, key: str):
        self._key = key

    def _get_current_context(self) -> Any:
        context = _PARAGON.get_context()
        return context[self._key]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_current_context(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            obj = self._get_current_context()
            setattr(obj, name, value)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        obj = self._get_current_context()
        return obj(*args, **kwargs)

    def __str__(self) -> str:
        return str(self._get_current_context())

    def __repr__(self) -> str:
        return repr(self._get_current_context())

    def __bool__(self) -> bool:
        return bool(self._get_current_context())

    def __len__(self) -> int:
        return len(self._get_current_context())

    def __iter__(self) -> Iterator[Any]:
        return iter(self._get_current_context())

    def __getitem__(self, key: Any) -> Any:
        return self._get_current_context().get(key)

    def __setitem__(self, key, value) -> None:
        self._get_current_context().set(key, value)

    def __contains__(self, item: Any) -> bool:
        return item in self._get_current_context()

    def __eq__(self, other: Any) -> bool:
        return self._get_current_context() == other

    def __hash__(self) -> int:
        return hash(self._get_current_context())


session = _ContextProxy('session')
monitor = _ContextProxy('monitor')
report = _ContextProxy('report')