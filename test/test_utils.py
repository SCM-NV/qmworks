"""Tests for :mod:`qmflows.utils`."""

import shutil
from os.path import isdir
from io import TextIOBase, StringIO
from contextlib import AbstractContextManager

from assertionlib import assertion
from scm.plams import init, finish

from qmflows.utils import to_runtime_error, file_to_context, init_restart, InitRestart
from qmflows.test_utils import PATH_MOLECULES, PATH

PSF_STR: str = """
PSF EXT

    10 !NATOM
     1 MOL1     1        LIG      C        C331   -0.272182       12.010600        0
     2 MOL1     1        LIG      C        C321   -0.282182       12.010600        0
     3 MOL1     1        LIG      C        C2O3    0.134065       12.010600        0
     4 MOL1     1        LIG      O        O2D2   -0.210848       15.999400        0
     5 MOL1     1        LIG      O        O2D2   -0.210848       15.999400        0
     6 MOL1     1        LIG      H        HGA2    0.087818        1.007980        0
     7 MOL1     1        LIG      H        HGA2    0.087818        1.007980        0
     8 MOL1     1        LIG      H        HGA3    0.087818        1.007980        0
     9 MOL1     1        LIG      H        HGA3    0.087818        1.007980        0
    10 MOL1     1        LIG      H        HGA3    0.087818        1.007980        0
"""


def _test_function(settings, key, value, mol):
    raise Exception('test')


def test_to_runtime_error() -> None:
    """Tests for :func:`to_runtime_error`."""
    args = (None, '_test_function', None, None)
    func = to_runtime_error(_test_function)
    assertion.assert_(func, *args, exception=RuntimeError)


def test_file_to_context() -> None:
    """Tests for :func:`file_to_context`."""
    path_like = PATH_MOLECULES / 'mol.psf'
    file_like = StringIO(PSF_STR)

    cm1 = file_to_context(path_like)
    cm2 = file_to_context(file_like)
    assertion.isinstance(cm1, AbstractContextManager)
    assertion.isinstance(cm2, AbstractContextManager)
    assertion.isinstance(cm1.__enter__(), TextIOBase)
    assertion.isinstance(cm2.__enter__(), TextIOBase)

    sequence = range(10)
    assertion.assert_(file_to_context, sequence, require_iterator=False)
    assertion.assert_(file_to_context, sequence, require_iterator=True, exception=TypeError)

    assertion.assert_(file_to_context, None, exception=TypeError)
    assertion.assert_(file_to_context, [1, 2], exception=TypeError)
    assertion.assert_(file_to_context, 5.0, exception=TypeError)


def test_restart_init() -> None:
    """Tests for :func:`restart_init` and :class:`RestartInit`."""
    workdir = PATH / 'plams_workdir'
    try:
        init(PATH)
        finish()
        assertion.isdir(workdir)

        init_restart(PATH)
        assertion.isdir(workdir)
        assertion.isdir(f'{workdir}.002', invert=True)
        finish()

        with InitRestart(PATH):
            assertion.isdir(workdir)
            assertion.isdir(f'{workdir}.002', invert=True)

    finally:
        shutil.rmtree(workdir) if isdir(workdir) else None
        shutil.rmtree(f'{workdir}.002') if isdir(f'{workdir}.002') else None
