"""Mock orca funcionality."""
import numpy as np
from assertionlib import assertion
from pytest_mock import mocker
from scm.plams import Molecule

from qmflows import Settings, orca
from qmflows.packages import Result, package_properties
from qmflows.test_utils import PATH, PATH_MOLECULES

workdir = PATH / "output_orca"


def test_orca_mock(mocker):
    """Mock a call to orca."""
    methanol = Molecule(PATH_MOLECULES / "methanol.xyz")

    s = Settings()
    s.specific.orca.main = "RKS B3LYP SVP Opt NumFreq TightSCF SmallPrint"
    # print the orbitals
    s.specific.orca.scf = " print[p_mos] 1"
    job = orca(s, methanol)

    run_mocked = mocker.patch("qmflows.run")
    jobname = "ORCAjob"
    dill_path = workdir / jobname / "ORCAjob.dill"
    plams_dir = workdir / jobname
    adf_properties = package_properties["orca"]
    run_mocked.return_value = Result(s, methanol, jobname, dill_path=dill_path,
                                     plams_dir=plams_dir, properties=adf_properties)
    rs = run_mocked(job)

    assertion.isfinite(rs.energy)
    assertion.isfinite(rs.runtime)
    assertion.isfinite(np.sum(rs.dipole))
    # steps until convergence
    assertion.eq(rs.optcycles, 8)

    # Check that hessian is symmetric
    hess = rs.hessian
    assertion.isclose(np.sum(hess - hess.T), 0.0)

    # frequencies
    frequencies = rs.frequencies
    assertion.len_eq(frequencies, 18)

    # Normal modes
    normal_modes = rs.normal_modes
    assertion.shape_eq(normal_modes, (18, 18))

    # Orbitals
    orbs = rs.orbitals
    assert np.isfinite(np.sum(orbs.eigenVals))  # eigenvalues
