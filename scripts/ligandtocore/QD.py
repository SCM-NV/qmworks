import copy
import os
import itertools
import time

from scm.plams import (Atom, MoleculeError)
from qmflows import molkit

import QD_functions as qd_scripts


def prep_core(core, core_folder, dummy=0, opt=True):
    """
    Function that handles all core operations.
    """
    # Checks the if the dummy is a string (atomic symbol) or integer (atomic number)
    if isinstance(dummy, str):
        dummy = Atom(symbol=dummy).atnum

    # Optimize the core with RDKit UFF if opt = True. Returns a RDKit molecule
    if opt:
        core = qd_scripts.global_minimum(core, core_folder)

    # Returns the indices (integer) of all dummy atom ligand placeholders in the core
    # An additional dummy atom is added at the core center of mass for orientating the ligands
    core_indices = [(i + 1) for i, atom in enumerate(core.atoms) if atom.atnum == dummy]
    core_indices.reverse()
    core.add_atom(Atom(atnum=0, coords=(core.get_center_of_mass())))

    # Set a number of atomic properties
    qd_scripts.set_pdb(core, 'COR', is_core=True)

    # Returns an error if no dummy atoms were found
    if not core_indices:
        raise MoleculeError(Atom(atnum=dummy).symbol +
                            ' was specified as dummy atom, yet no dummy atoms were found')
    else:
        return core_indices


def prep_ligand(ligand, ligand_folder, database, opt=True, split=True):
    """
    Function that handles all ligand operations,
    """
    # Handles all interaction between the database, the ligand and the ligand optimization
    ligand, database_entry = qd_scripts.manage_ligand(ligand, ligand_folder, opt, database)

    # Identify functional groups within the ligand and add a dummy atom to the center of mass.
    ligand_list, ligand_indices = qd_scripts.find_substructure(ligand, split)
    for ligand in ligand_list:
        ligand.add_atom(Atom(atnum=0, coords=ligand.get_center_of_mass()))

    return ligand_list, ligand_indices, database_entry


def prep_qd(core, ligand, core_indices, ligand_index, qd_folder):
    """
    Function that handles all quantum dot (qd, i.e. core + all ligands) operations.
    """
    # Rotate and translate all ligands to their position on the core.
    # Returns a list of PLAMS molecules and atomic indices.
    core = copy.deepcopy(core)
    ligand_list = [qd_scripts.rotate_ligand(core, ligand, core_index, ligand_index, i)
                   for i, core_index in enumerate(core_indices)]

    ligand_list, ligand_indices = zip(*ligand_list)
    core.delete_atom(core[-1])

    # Prepare the .pdb filename as a string.
    core_name = core.get_formula()
    ligand_formula = ligand_list[0].get_formula()
    ligand_heteroatom = ligand[ligand_index].symbol
    ligand_name = ligand_formula + '_@_' + ligand_heteroatom + str(ligand_index)
    pdb_name = str('core_' + core_name + '___ligand_' + ligand_name)

    # Attach the rotated ligands to the core, returning the resulting strucutre (PLAMS Molecule).
    qd = qd_scripts.combine_qd(core, ligand_list)

    # indices of all the atoms in the core and the ligand heteroatom anchor.
    qd_indices = [qd.atoms.index(atom) + 1 for atom in ligand_indices]
    qd_indices += [i + 1 for i, atom in enumerate(core)]

    qd.write(os.path.join(qd_folder, pdb_name + '.xyz'))
    molkit.writepdb(qd, os.path.join(qd_folder, pdb_name + '.pdb'))
    print('core + ligands:\t\t\t' + pdb_name + '.pdb')

    return qd, pdb_name, qd_indices





def prep_prep(path, dir_name_list, input_cores, input_ligands, smiles_extension, column, row,
              dummy, database_name, use_database, core_opt, ligand_opt, qd_opt, maxiter, split):
    """
    function that handles all tasks related to prep_core, prep_ligand and prep_qd.
    """
    # The start
    time_start = time.time()
    print('\n')

    # Managing the result directories
    core_folder, ligand_folder, qd_folder = [qd_scripts.create_dir(name, path=path) for name in
                                             dir_name_list]

    # Imports the cores and ligands
    core_list = qd_scripts.read_mol(core_folder, input_cores, column, row, smiles_extension)
    ligand_list = qd_scripts.read_mol(ligand_folder, input_ligands, column, row, smiles_extension)

    # Return the indices of the core dummy atoms
    core_indices = [prep_core(core, core_folder, dummy, core_opt) for core in core_list]

    # Open the ligand database and check if the specified ligand(s) is already present
    if use_database:
        database = qd_scripts.read_database(ligand_folder, database_name)
    else:
        database = [[], [], [], [], []]

    ligand_list = [prep_ligand(ligand, ligand_folder, database, ligand_opt, split) for ligand in
                   ligand_list]

    # Formating of ligand_list
    ligand_list, ligand_indices, database_entries = zip(*ligand_list)
    ligand_indices = list(itertools.chain(*ligand_indices))
    ligand_list = itertools.chain(*ligand_list)

    # Write new entries to the ligand database
    if use_database:
        qd_scripts.write_database(database_entries, ligand_folder, database)

    # Combine the core with the ligands, yielding qd
    qd_list = [prep_qd(core, ligand, core_indices[i], ligand_indices[j], qd_folder) for i, core in
               enumerate(core_list) for j, ligand in enumerate(ligand_list)]

    # Formating of qd_list
    qd_list, pdb_name_list, qd_indices = zip(*qd_list)

    # Check if the ADF environment variables are set and optimize the qd with the core frozen
    if qd_opt:
        sys_var = ['ADFBIN', 'ADFHOME', 'ADFRESOURCES', 'SCMLICENSE']
        sys_var_exists = [item in os.environ for item in sys_var]
        for i, item in enumerate(sys_var_exists):
            if not item:
                print('WARNING: The environment variable ' + sys_var[i] + ' has not been set')
        if False in sys_var_exists:
            raise MoleculeError('One or more ADF environment variables have not been set,' +
                                ' aborting geometry optimization.')
        for i, qd in enumerate(qd_list):
            qd_scripts.prep_ams_job(qd, pdb_name_list[i], qd_folder, qd_indices[i], maxiter)

    # The End
    time_end = time.time()
    print('\nTotal elapsed time:\t\t' + '%.4f' % (time_end - time_start) + ' sec')




# Argument list
prep_prep_args = {
    'path': r'/Users/basvanbeek/Documents/CdSe/Week_5',
    'dir_name_list': ['core', 'ligand', 'QD'],
    'input_cores': 'Cd68Se55.xyz',
    'input_ligands': ['CCCCCCCCC([O-])=O.CC[N+](CC)(CC)CC', 'OCCCCCCCCC'],
    'smiles_extension': '.txt',
    'column': 0,
    'row': 0,
    'dummy': 'Cl',
    'database_name': 'ligand_database.txt',
    'use_database': True,
    'core_opt': False,
    'ligand_opt': True,
    'qd_opt': False,
    'maxiter': 10000,
    'split': True
}


# Runs the script: add ligand to core and optimize (UFF) the resulting qd with the core frozen
prep_prep(**prep_prep_args)

"""
path =              The path where the input and output directories will be saved. Set to
                    os.getcwd() to use the current directory.
dir_name_list =     Names of the to be created directories in path.
input_cores =       The input core(s) as either .xyz, .pdb, .mol, SMILES string, plain text file
                    with SMILES string or a list containing any of the above objects.
input_ligands =     Same as input_cores, except for the ligand(s).
smiles_extension =  Extension of a SMILES string containg plain text file. Relevant if such a file
                    is chosen for input_cores or input_ligands.
column =            The column containing the SMILES strings in the plain text file.
row =               The amount of rows to be ignored in the SMILES string containing column.
                    Should be used when e.g. the first row does not contain a SMILES string
dummy =             The atomic number of atomic symbol of the atoms in the core that should be
                    should be replaced with ligands.
database_name =     Name plus extension of the (to be) created ligand database.
use_database =      Export/import results from the (to be) created ligand database. No database will
                    be used and/or maintained when set to False.
core_opt =          Attempt to find the core global minimum using RDKit UFF.
                    WARNING: enabling this will probably ruin the core if care is not taken!
                    Should work fine for organic cores.
ligand_opt =        Attempt to find the ligand global minimum using RDKit UFF.
qd_opt =            Optimize the quantum dot (qd)(i.e core + all ligands) using ADF UFF.
maxiter =           The maximum number of geometry iteration during qd_opt.
split =             Should the ligand be attached to the core in its entirety or should a
                    hydrogen atom/counterion first be removed? Examples are provided below:
                    True:  HO2CR -> -O2CR,  X-.NH4+ -> NH4+  &  Na+.-O2CR -> -O2CR
                    False: HO2CR -> HO2CR,  NH4+ -> NH4+  & -O2CR -> -O2CR
"""
