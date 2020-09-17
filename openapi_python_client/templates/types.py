""" Contains some shared types for properties """
import contextlib
import os
from dataclasses import dataclass
from typing import BinaryIO, Generator, Optional, TextIO, Tuple, Union


@dataclass
class File:
    """ Contains information for file uploads """
    payload: Union[BinaryIO, TextIO]
    file_name: str = None
    mime_type: Optional[str] = None

    def to_tuple(self) -> Tuple[str, Union[BinaryIO, TextIO], Optional[str]]:
        """ Return a tuple representation that httpx will accept for multipart/form-data """
        return self.file_name, self.payload, self.mime_type


    @classmethod
    @contextlib.contextmanager
    def from_local_file(cls, path: str, mime_type: Optional[str] = None) -> Generator['File', None, None]:
        with open(path, 'rb') as f:
            yield cls(payload=f, file_name=os.path.basename(path), mime_type=mime_type)


__all__ = ["File"]
