"""
providers/__init__.py – provider registry and auto-detection.
"""
from .dmrv import DMRVProvider
from .eon_del import EONDelProvider
from .elmu import ELMUProvider
from .e2_hungary import E2HungaryProvider
from .mvm_next import MVMNextProvider
from .edv import EDVProvider
from .fovarosi_vizmuvek import FovarosiVizmuvekProvider
from .heves_megyei import HevesMegyeiProvider
from .tettye import TettyeProvider
from .base import BaseProvider

# Order matters: put more-specific providers before generic fallbacks.
_PROVIDERS: list[BaseProvider] = [
    ELMUProvider(),          # must come before EONDelProvider (both say "E.ON" in some text)
    EONDelProvider(),
    E2HungaryProvider(),
    MVMNextProvider(),
    DMRVProvider(),
    EDVProvider(),
    FovarosiVizmuvekProvider(),
    HevesMegyeiProvider(),
    TettyeProvider(),
]


def detect_provider(pages: list[str]) -> BaseProvider | None:
    """Return the first provider whose detect() returns True, or None."""
    for provider in _PROVIDERS:
        if provider.detect(pages):
            return provider
    return None
