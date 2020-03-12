"""Utility functions for the QMFlows tests.

Index
-----
.. currentmodule:: qmflows.test_utils
.. autosummary::
    delete_output
    get_mm_settings
    PATH

API
---
.. autofunction:: delete_output
.. autofunction:: get_mm_settings
.. autodata:: PATH
    :annotation: : pathlib.Path

"""

import os
import shutil
from pathlib import Path
from typing import Union, Callable, Any
from functools import wraps

from .settings import Settings

__all__ = ['delete_output', 'get_mm_settings', 'PATH']

#: The path to the ``tests/test_files`` directory.
PATH = Path('test') / 'test_files'


def delete_output(delete_db: Union[Callable, bool] = True,
                  delete_workdir: bool = True) -> Callable:
    """A decorator for deleting ``cache.db`` and the plams workdir after a test is done.

    Examples
    --------
    Can be used in one of two ways:

    .. code:: python

        >>> from qmflows.test_utils import delete_output

        >>> @delete_output
        >>> def test1(...):
        ...     ...

        >>> @delete_output(delete_db=True, delete_workdir=False)
        >>> def test2(...):
        ...     ...

    Parameters
    ----------
    delete_db : :class:`bool`
        If ``True``, delete the ``cache.db`` file.

    delete_workdir : :class:`bool`
        If ``True``, delete the PLAMS workdir located at "{workdir}".

    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                ret = func(*args, **kwargs)
            finally:
                if delete_db and os.path.isfile('cache.db'):
                    os.remove('cache.db')

                workdir = PATH / 'plams_workdir'
                if delete_workdir and os.path.isdir(workdir):
                    shutil.rmtree(workdir)
                    _del_all_workdir(workdir)
            return ret
        return wrapper

    if callable(delete_db):
        func, delete_db = delete_db, True
        return decorator(func)
    else:
        return decorator


delete_output.__doc__ = delete_output.__doc__.format(workdir=PATH / 'plams_workdir')


def _del_all_workdir(workdir: Union[str, os.PathLike]) -> None:
    """Delete all working directories with a ``"workdir.{iii}"``-style name."""
    i = 2
    while True:
        workdir_i = f'{workdir}.{str(i).zfill(3)}'
        if os.path.isdir(workdir_i) and i < 1000:
            shutil.rmtree(workdir_i)
            i += 1
        else:
            break

def get_mm_settings() -> Settings:
    """Construct and return CP2K settings for classical forcefield calculations.

    Note that these settings will still have to be updated with a job-specific template.

    """
    charge = Settings()
    charge.param = 'charge'
    charge.Cd = 0.9768
    charge.Se = -0.9768
    charge.O_1 = -0.4704
    charge.C_1 = 0.4524

    lj = Settings()
    lj.param = 'epsilon', 'sigma'
    lj.unit = 'kjmol', 'nm'
    lj['Cd Cd'] = 0.3101, 0.1234
    lj['Cd O_1'] = 1.8340, 0.2471
    lj['Cd Se'] = 1.5225, 0.2940
    lj['Se C_1'] = 1.6135, 0.3526
    lj['Se Se'] = 0.4266, 0.4852
    lj['H Se'] = 0.4734, 0.3297
    lj['H Cd'] = 0.4191, 0.2554

    s = Settings()
    s.psf = PATH / 'Cd68Se55_26COO.psf'
    s.prm = PATH / 'Cd68Se55_26COO.prm'
    s.charge = charge
    s.lennard_jones = lj
    return s
