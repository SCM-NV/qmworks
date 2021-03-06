"""Test package wrapper funcionality."""
import os
import warnings
from typing import Type

import pytest
from noodles.interface import PromisedObject
from scm.plams import ADFJob, AMSJob, from_smiles
from scm.plams.core.basejob import Job
from assertionlib import assertion


from qmflows import PackageWrapper, run, Settings
from qmflows.utils import InitRestart
from qmflows.packages.packages import Result
from qmflows.packages.SCM import ADF_Result
from qmflows.packages.package_wrapper import ResultWrapper
from qmflows.test_utils import delete_output, PATH

ADF_ENVIRON = frozenset({'AMSBIN', 'AMSHOME', 'AMSRESOURCES', 'SCMLICENSE'})
HAS_ADF: bool = ADF_ENVIRON.issubset(os.environ.keys())


def _get_result(promised_object: PromisedObject, job: Type[Job]) -> Result:
    """Call :func:`qmflows.run` or manually construct a :class:`qmflows.Result` object."""
    if HAS_ADF:  # ADF has been found; run it
        return run(promised_object, path=PATH, folder='workdir')

    dill_map = {ADFJob: PATH / 'ADFJob.dill', AMSJob: PATH / 'AMSJob.dill'}
    result_map = {ADFJob: ADF_Result, AMSJob: ResultWrapper}

    result_type = result_map[job]
    warnings.warn("Mocking ADF results; failed to identify the following ADF environment "
                  f"variables: {set(ADF_ENVIRON.difference(os.environ.keys()))!r}")

    # Manually construct a (barely) functioning qmflows.Result object.
    # Only the _result and _results attributes are actually assigned.
    # The object is an instance of the correct Result subclass and it's
    # job status == 'successful', so that's enough for the actual test.
    ret = result_type.__new__(result_type)
    ret._results_open = False
    with InitRestart(path=PATH, folder='workdir'):
        ret._results = dill_map[job]
    return ret


@pytest.mark.slow
@delete_output
def test_package_wrapper() -> None:
    """Tests for :class:`PackageWrapper<qmflows.packages.package_wrapper.PackageWrapper>`."""
    s1 = Settings()
    s1.input.ams.Task = 'GeometryOptimization'
    s1.input.ams.GeometryOptimization.Convergence.Gradients = 1.0e-4
    s1.input.ams.Properties.NormalModes = 'true'
    s1.input.DFTB.Model = 'DFTB3'
    s1.input.DFTB.ResourcesDir = 'DFTB.org/3ob-3-1'

    s2 = Settings()
    s2.input.basis.type = 'DZP'
    s2.input.basis.core = 'None'
    s2.input.basis.createoutput = 'None'

    mol = from_smiles('O')  # H2O

    job1 = PackageWrapper(AMSJob)(s1, mol, name='amsjob')
    result1 = _get_result(job1, AMSJob)
    assertion.isinstance(result1, ResultWrapper)
    assertion.eq(result1.results.job.status, 'successful')

    job2 = PackageWrapper(ADFJob)(s2, mol, name='adfjob')
    result2 = _get_result(job2, ADFJob)
    assertion.isinstance(result2, ADF_Result)
    assertion.eq(result2.results.job.status, 'successful')
