from agent_tools.pdfadapter import PDFAdapter
from pathlib import Path


profile_path = (
    Path(__file__).cwd()
    / "data/sequential_fit/Ni_PDF_20250922-220901_36ae05_5K.gr"
)
structure_path = Path(__file__).cwd() / "data/Ni.cif"
adapter = PDFAdapter()
adapter.init_profile(
    str(profile_path), xmin=1.5, xmax=50, dx=0.01, qmax=25, qmin=0.1
)
adapter.init_structures([str(structure_path)])
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
adapter.set_initial_variable_values(initial_pdfadapter_pv_dict)
adapter.refine_variables(
    [
        "a_1",
        "s0",
        "Uiso_0_1",
        "delta2_1",
        "qdamp",
        "qbroad",
    ]
)
out_dict = adapter.save_results(mode="dict", filename="fit_results.json")
