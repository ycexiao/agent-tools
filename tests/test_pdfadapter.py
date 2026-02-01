from agent_tools import pdfadapter
from pathlib import Path
from scipy.optimize import least_squares
import sys

sys.path.append(str(Path(__file__).parent / "diffpycmi_scripts.py"))
from diffpycmi_scripts import make_recipe  # noqa: E402


def test_pdfadapter():

    # diffpy_cmi fitting
    structure_path = Path(__file__).parent / "data" / "Ni.cif"
    profile_path = Path(__file__).parent / "data" / "Ni.gr"
    diffpycmi_recipe = make_recipe(str(structure_path), str(profile_path))
    diffpycmi_recipe.fithooks[0].verbose = 0
    diffpycmi_recipe.fix("all")
    tags = ["lat", "scale", "adp", "d2", "all"]
    for tag in tags:
        diffpycmi_recipe.free(tag)
        least_squares(
            diffpycmi_recipe.residual,
            diffpycmi_recipe.values,
            x_scale="jac",
        )
    diffpy_pv_dict = {}
    for pname, parameter in diffpycmi_recipe._parameters.items():
        diffpy_pv_dict[pname] = parameter.value
    # pdfadapter fitting
    adapter = pdfadapter.PDFAdapter()
    adapter.init_profile(
        profile_path, xmin=1.5, xmax=50, dx=0.01, qmax=25, qmin=0.1
    )
    adapter.init_structures([structure_path])
    adapter.init_contribution()
    adapter.init_recipe()
    initial_pdfadapter_pv_dict = {
        "s0": 0.4,
        "qdamp": 0.04,
        "qbroad": 0.02,
        "a_1": 3.52,
        "Uiso_0_1": 0.005,
        "delta2_1": 2,
    }
    adapter.apply_parameter_values(initial_pdfadapter_pv_dict)

    fit_pname = ["a_1", "s0", "Uiso_0_1", "delta2_1", "qdamp", "qbroad"]
    for pname in fit_pname:
        adapter.recipe.free(pname)
        least_squares(
            adapter.recipe.residual,
            adapter.recipe.values,
            x_scale="jac",
        )
    diffpyname_to_adaptername = {
        "fcc_Lat": "a_1",
        "s1": "s0",
        "fcc_ADP": "Uiso_0_1",
        "Ni_Delta2": "delta2_1",
        "Calib_Qdamp": "qdamp",
        "Calib_Qbroad": "qbroad",
    }
    pdfadapter_pv_dict = {}
    for pname, parameter in adapter.recipe._parameters.items():
        pdfadapter_pv_dict[pname] = parameter.value
    for diffpy_pname, adapter_pname in diffpyname_to_adaptername.items():
        assert (
            abs(
                diffpy_pv_dict[diffpy_pname]
                - pdfadapter_pv_dict[adapter_pname]
            )
            < 1e-5
        )
