import inspect
from pathlib import Path
from typing import get_type_hints, get_origin, get_args
from types import UnionType

from autopcb.datatypes.mixins import DataclassSerializerMixin

null_value_in_cache_placeholder = 'None'

error_hint = (f"The current implementation of the cache only supports "
              f"functions with the args of type (self, the_arg: str)")


def cache_returned_dataclass_to_disk(func):
    """ Cache a function's return value to disk. Currently only supports functions that are
     class methods with one additional arg that is a `str` and that have a return type
     that inherits DataclassSerializerMixin.
     Later we should add support for caching arbitrary arguments, or return values """
    # Check that we support caching this function
    # later it would be cool to add support to caching arbitrary arguments,
    # by serializing the args by recursively sorting dicts, etc.
    # so we can do a deep equal on the hash of the arg's serialized repr
    func_params = list(inspect.signature(func).parameters.values())
    if len(func_params) != 2:
        raise NotImplementedError(f"The function being cached doesn't have exactly two args. " + error_hint)
    if func_params[0].name != 'self':
        raise NotImplementedError(f"The function being cached doesn't have it's 1st arg as `self` "
                                  f"(it should be a class's method). " + error_hint)
    if func_params[1].annotation is not str:
        raise NotImplementedError(f"The function being cached doesn't have it's 2nd arg annotated "
                                  f"as a `str` " + error_hint)

    # Check that the return type is valid
    return_type = get_type_hints(func)['return']

    # Handle Optional[T] which is Union[T, None]
    the_dataclass = return_type
    if get_origin(return_type) is UnionType:
        # Get the non-None type from Union
        type_args = get_args(return_type)
        non_none_types = [t for t in type_args if t is not type(None)]
        if len(non_none_types) != 1:
            raise Exception(f"The function that's being cached has a return type '{return_type}' "
                            f"that is not a simple Optional type")
        the_dataclass = non_none_types[0]
    if not issubclass(the_dataclass, DataclassSerializerMixin):
        raise Exception(f"The function that's being cached has a return type '{the_dataclass}'"
                        f" that does not inherit from "
                        f"DataclassSerializerMixin, which is required since .dumps() and .from_json() is "
                        f"used to serialize it to a file.")

    is_async = inspect.iscoroutinefunction(func)
    
    if is_async:
        async def async_wrapper(*args):
            folder_path = Path(f'cache/{func.__qualname__}/')
            folder_path.mkdir(parents=True, exist_ok=True)

            cache_file_path = folder_path / args[-1]

            # If file exists, load from cache
            if cache_file_path.exists():
                file_cache_content = cache_file_path.read_text()
                if file_cache_content == null_value_in_cache_placeholder:
                    return None
                else:
                    try:
                        return the_dataclass.from_json(file_cache_content)
                    except Exception:
                        # if the file is corrupt, delete it
                        cache_file_path.unlink()
                        # and continue executing the function (uncached) as normal

            # If file does not exist (not in cache), compute the result
            result = await func(*args)

            # Only save to cache if result is not None
            if result is None:
                cache_file_path.write_text(null_value_in_cache_placeholder)
            else:
                cache_file_path.write_text(result.dumps())

            return result
        
        return async_wrapper
    else:
        def sync_wrapper(*args):
            folder_path = Path(f'cache/{func.__qualname__}/')
            folder_path.mkdir(parents=True, exist_ok=True)

            cache_file_path = folder_path / args[-1]

            # If file exists, load from cache
            if cache_file_path.exists():
                file_cache_content = cache_file_path.read_text()
                if file_cache_content == null_value_in_cache_placeholder:
                    return None
                else:
                    try:
                        return the_dataclass.from_json(file_cache_content)
                    except Exception:
                        # if the file is corrupt, delete it
                        cache_file_path.unlink()
                        # and continue executing the function (uncached) as normal

            # If file does not exist (not in cache), compute the result
            result = func(*args)

            # Only save to cache if result is not None
            if result is None:
                cache_file_path.write_text(null_value_in_cache_placeholder)
            else:
                cache_file_path.write_text(result.dumps())

            return result

        return sync_wrapper
