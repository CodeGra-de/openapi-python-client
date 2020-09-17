import io
import json
from typing import Any, Callable, Dict, List, Union


def response_code_matches(code: int, expected: Union[str, int]) -> bool:
    if expected == 'default':
        return True
    elif isinstance(expected, int) and code == expected:
        return True
    return isinstance(expected, str) and code > 100 and code / 100 == int(
        expected[0])


def try_any(lst: List[Callable]) -> Any:
    err = Exception()

    for item in lst:
        try:
            return item()
        except BaseException as exc:
            err = exc

    raise err


def to_multipart(dct: Dict[str, Any]) -> Dict[str, Any]:
    res = {}
    for key, value in dct.items():
        if isinstance(value, list):
            for idx, subval in enumerate(value):
                assert isinstance(subval, tuple)
                res[f'{key}_{idx}'] = subval
        elif isinstance(value, tuple):
            res[key] = value
        else:
            res[key] = (key, io.StringIO(json.dumps(value)))

    return res


def maybe_to_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return {k: maybe_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [maybe_to_dict(sub) for sub in obj]
    if isinstance(obj, (type(None), str, int, float)):
        return obj
    return obj.to_dict()
