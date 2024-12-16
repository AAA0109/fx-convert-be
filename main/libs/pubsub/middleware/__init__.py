from .logging_middleware import LoggingMiddleware
from .interface import MiddlewareInterface

import importlib

_middlewares = []


def register_middleware(config: 'Config', **kwargs):
    paths = config.middleware
    global _middlewares
    _middlewares = []
    for path in paths:
        *module_parts, middleware_class = path.split(".")
        module_path = ".".join(module_parts)
        module = importlib.import_module(module_path)
        middleware = getattr(module, middleware_class)()
        middleware.setup(config, **kwargs)
        _middlewares.append(middleware)


def run_middleware_hook(hook_name, *args, **kwargs):
    for middleware in _middlewares:
        if hasattr(middleware, hook_name):
            getattr(middleware, hook_name)(*args, **kwargs)
