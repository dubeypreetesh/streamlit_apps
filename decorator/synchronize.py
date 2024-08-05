'''
Created on 26-Jun-2024

@author: ongraph
'''
from functools import wraps


def synchronized(lock):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)

        return wrapper

    return decorator
