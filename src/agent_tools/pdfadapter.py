from diffpy.srfit.pdf import PDFParser
from diffpy.srfit.structure import constrainAsSpaceGroup
from diffpy.structure.parsers import getParser
from diffpy.srfit.fitbase import (
    FitContribution,
    FitRecipe,
    Profile,
)
from diffpy.srfit.pdf import PDFGenerator
import numpy
import warnings
from pathlib import Path


class PDFAdapter:
    """Adapter to expose PDF fitting interface.

    Attributes
    ----------
    recipe : FitRecipe
        The FitRecipe object managing the fitting process.
    profile : Profile
        The Profile object representing the experimental PDF data.
    pdfgenerators : list of PDFGenerator
        The list of PDFGenerator objects for each structure.
    contribution : FitContribution
        The FitContribution object combining the PDF generators.

    Methods
    -------
    load_inputs(inputs)
        Load inputs to initialize the adapter.
    apply_parameter_values(pv_dict)
        Update parameter values from the provided dictionary.
    get_parameter_values()
        Get current parameter values as a dictionary.
    show_parameters()
        Show current parameter values and their fix/free status.
    apply_action()
        Generate operations to be performed in the workflow.
    generate_observation()
    """

    required_keys = [
        "structure_path(s)",
        "profile_path",
    ]

    def __init__(self):
        pass

    def init_profile(
        self,
        profile_path: Path,
        qmin=None,
        qmax=None,
        xmin=None,
        xmax=None,
        dx=None,
    ):
        """
        Load and initialize the PDF profile from the given file path with
        some optional parameters.

        The target output, FitRecipe, requires a profile object, multiple
        PDFGenerator objects, and a FitContribution object combining them. This
        method initializes the profile object.

        Parameters
        ----------
        profile_path : Path
            The path to the experimental PDF profile file.
        qmin : float, optional
            The minimum Q value for PDF calculation. Default is None.
        qmax : float, optional
            The maximum Q value for PDF calculation. Default is None.
        xmin : float, optional
            The minimum r value for PDF calculation. Default is None.
        xmax : float, optional
            The maximum r value for PDF calculation. Default is None.
        dx : float, optional
            The r step size for PDF calculation. Default is None.
        """
        profile = Profile()
        parser = PDFParser()
        parser.parseString(profile_path.read_text())
        profile.loadParsedData(parser)
        if qmin:
            profile.meta["qmin"] = qmin
        if qmax:
            profile.meta["qmax"] = qmax
        profile.setCalculationRange(xmin=xmin, xmax=xmax, dx=dx)
        self.profile = profile

    def init_structures(self, structure_paths: list[Path], run_parallel=True):
        """
        Load and initialize the structures from the given file paths, and
        generate corresponding PDFGenerator objects.

        The target output, FitRecipe, requires a profile object, multiple
        PDFGenerator objects, and a FitContribution object combining them. This
        method creates the PDFGenerator objects from the structure files.

        Must be called after init_profile.

        Parameters
        ----------
        structure_paths : list of Path
            The list of paths to the structure files (CIF format).

        Notes
        -----
        Planned features:
        - Support cif file manipulation.
            - Add/Remove atoms.
            - symmetry operations?
        """
        if isinstance(structure_paths, Path):
            structure_paths = [structure_paths]
        structures = []
        spacegroups = []
        pdfgenerators = []
        if run_parallel:
            try:
                import psutil
                import multiprocessing
                from multiprocessing import Pool

                syst_cores = multiprocessing.cpu_count()
                cpu_percent = psutil.cpu_percent()
                avail_cores = numpy.floor(
                    (100 - cpu_percent) / (100.0 / syst_cores)
                )
                ncpu = int(numpy.max([1, avail_cores]))
                pool = Pool(processes=ncpu)
            except ImportError:
                warnings.warn(
                    "\nYou don't appear to have the necessary packages for "
                    "parallelization. Proceeding without parallelization."
                )
                run_parallel = False

        for i, structure_path in enumerate(structure_paths):
            stru_parser = getParser("cif")
            structure = stru_parser.parse(structure_path.read_text())
            sg = getattr(stru_parser, "spacegroup", None)
            spacegroup = sg.short_name if sg is not None else "P1"
            structures.append(structure)
            spacegroups.append(spacegroup)
            pdfgenerator = PDFGenerator(f"G{i+1}")
            pdfgenerator.setStructure(structure)
            if run_parallel:
                pdfgenerator.parallel(ncpu=ncpu, mapfunc=pool.map)
            pdfgenerators.append(pdfgenerator)
        self.spacegroups = spacegroups
        self.pdfgenerators = pdfgenerators

    def init_contribution(self, equation_string=None):
        """
        Initialize the FitContribution object combining the PDF generators and
        the profile.

        The target output, FitRecipe, requires a profile object, multiple
        PDFGenerator objects, and a FitContribution object combining them. This
        method creates the FitContribution object combining the profile and PDF
        generators.

        Must be called after init_profile and init_structures.

        Parameters
        ----------
        equation_string : str, optional
            The equation string defining the contribution. If None, a default
            equation will be generated based on the number of phases.

        Notes
        -----
        Planned features:
        - Support registerFunction for custom equations.
        """
        contribution = FitContribution("pdfcontribution")
        contribution.setProfile(self.profile)
        for pdfgenerator in self.pdfgenerators:
            contribution.addProfileGenerator(pdfgenerator)
        number_of_phase = len(self.pdfgenerators)
        if equation_string is None:
            if number_of_phase == 1:
                equation_string = "s0*G1"
            else:
                equation_string = (
                    "s0*("
                    + "+".join(
                        [f"s{i+1}*G{i+1}" for i in range(number_of_phase - 1)]
                    )
                    + f"+(1-({'+'.join([f's{i+1}' for i in range(1, number_of_phase)])}))*G{number_of_phase}"  # noqa: E501
                    + ")"
                )
        contribution.setEquation(equation_string)
        self.contribution = contribution
        return self.contribution

    def init_recipe(
        self,
    ):
        """
        Initialize the FitRecipe object for the fitting process.

        The target output, FitRecipe, requires a profile object, multiple
        PDFGenerator objects, and a FitContribution object combining them. This
        method creates the FitRecipe object combining the profile, PDF generators,
        and contribution.

        Must be called after init_contribution.


        Notes
        -----
        Planned features:
        - support instructions to
            - add variables
            - constrain variables of the scatters
            - change symmetry constraints
        """
        recipe = FitRecipe()
        recipe.addContribution(self.contribution)
        qdamp = recipe.newVar("qdamp", fixed=False, value=0.04)
        qbroad = recipe.newVar("qbroad", fixed=False, value=0.02)
        for i, (pdfgenerator, spacegroup) in enumerate(
            zip(self.pdfgenerators, self.spacegroups)
        ):
            for pname in [
                "delta1",
                "delta2",
            ]:
                par = getattr(pdfgenerator, pname)
                recipe.addVar(par, name=pname + f"_{i+1}", fixed=False)
            if len(self.pdfgenerators) > 1:
                recipe.addVar(
                    getattr(self.contribution, f"s{i+1}"),
                    name=f"s{i+1}",
                    fixed=False,
                )
                recipe.restrain(f"s{i+1}", lb=0.0, ub=1.0)
            recipe.constrain(pdfgenerator.qdamp, qdamp)
            recipe.constrain(pdfgenerator.qbroad, qbroad)
            stru_parset = pdfgenerator.phase
            spacegroupparams = constrainAsSpaceGroup(stru_parset, spacegroup)
            for par in spacegroupparams.xyzpars:
                recipe.addVar(par, name=par.name + f"_{i+1}", fixed=False)
            for par in spacegroupparams.latpars:
                recipe.addVar(par, name=par.name + f"_{i+1}", fixed=False)
            for par in spacegroupparams.adppars:
                recipe.addVar(par, name=par.name + f"_{i+1}", fixed=False)
        recipe.addVar(self.contribution.s0, name="s0", fixed=False)
        recipe.fix("all")
        recipe.fithooks[0].verbose = 0
        self.recipe = recipe

    def apply_parameter_values(self, pv_dict: dict):
        """
        Update parameter values from the provided dictionary.

        Parameters
        ----------
        pv_dict : dict
            A dictionary mapping parameter names to their new values.
        """
        parameter_dict = {
            pname: parameter
            for pname, parameter in self.recipe._parameters.items()
        }
        for pname, pvalue in pv_dict.items():
            parameter_dict[pname].setValue(pvalue)
