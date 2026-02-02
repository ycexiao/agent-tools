from matplotlib import pyplot as plt
from bg_mpl_stylesheets.styles import all_styles
from diffpy.srreal.pdfcalculator import PDFCalculator
from diffpy.structure import loadStructure
from diffpy.srfit.pdf import PDFParser
from diffpy.srfit.fitbase import Profile
from pathlib import Path
from matplotlib.gridspec import GridSpec
from pyparsing import line

plt.style.use(all_styles["bg-style"])


def get_nth_ax(axes, n):
    if len(axes) == 1:
        return axes[0]
    else:
        return axes[n]


class Plotter:
    """
    A class for plotting data using Matplotlib with predefined styles.
    """

    def __init__(self):
        self.figures = {}
        self.colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    def get_fig_ax(self, fig_title: str):
        if fig_title in self.figures:
            fig = self.figures[fig_title]
            n_ax = len(fig.axes)
            old_axes_data = []
            for old_ax in fig.axes:
                x_values = []
                y_values = []
                line = old_ax.get_lines()[0]
                x_values = line.get_xdata()
                y_values = line.get_ydata()
                label = line.get_label()
                old_axes_data.append((x_values, y_values, label))
            fig.axes.clear()
            fig.clf()
            gs = GridSpec(n_ax + 1, 1, figure=fig)
            for i, (ox, oy, label) in enumerate(old_axes_data):
                ax_old = fig.add_subplot(gs[i, 0])
                ax_old.plot(ox, oy, label=label)
                ax_old.set_yticks([])
            ax = fig.add_subplot(gs[-1, 0])
        else:
            fig, ax = plt.subplots()
            fig.suptitle(fig_title)
            self.figures[fig_title] = fig
        return fig, ax

    def plot_structure(
        self,
        structure_path: str,
        fig_title: str,
        qmin=None,
        qmax=None,
        scale=None,
        delta1=None,
        delta2=None,
        qdamp=None,
        qbroad=None,
        rmin=None,
        rmax=None,
        rstep=None,
        slope=None,
        spdiameter=None,
        plot_kwargs={},
    ):
        fig, ax = self.get_fig_ax(fig_title)
        pdfcalc_kwargs = {
            "qmin": qmin,
            "qmax": qmax,
            "scale": scale,
            "delta1": delta1,
            "delta2": delta2,
            "qdamp": qdamp,
            "qbroad": qbroad,
            "rmin": rmin,
            "rmax": rmax,
            "rstep": rstep,
            "slope": slope,
            "spdiameter": spdiameter,
        }
        structure = loadStructure(structure_path)
        pdfcalc = PDFCalculator(
            **{k: v for k, v in pdfcalc_kwargs.items() if v is not None}
        )
        r0, g0 = pdfcalc(structure)
        ax.plot(
            r0,
            g0,
            label=Path(structure_path).stem + " PDF",
            **plot_kwargs,
        )
        ax.set_yticks([])
        fig.legend()

    def plot_profile(
        self,
        profile_path: str,
        fig_title: str,
        plot_kwargs={},
    ):
        fig, ax = self.get_fig_ax(fig_title)
        parser = PDFParser()
        parser.parseFile(profile_path)
        profile = Profile()
        profile.loadParsedData(parser)
        ax.plot(
            profile.xobs,
            profile.yobs,
            label=Path(profile_path).stem + " Profile",
            **plot_kwargs,
        )
        ax.set_yticks([])
        fig.legend()


if __name__ == "__main__":
    plotter = Plotter()
    plotter.plot_profile(
        "data/Ni.gr", fig_title="Ni", plot_kwargs={"color": plotter.colors[0]}
    )
    plotter.plot_structure(
        "data/Ni.cif",
        fig_title="Ni",
        rmin=1.5,
        rmax=50,
        rstep=0.01,
        qmin=0.1,
        qmax=25,
        qdamp=0.04,
        qbroad=0.02,
        plot_kwargs={"color": plotter.colors[1]},
    )
    plt.show()
    # diffpy.cmi plots
    # from agent_tools.diffpycmi_scripts import make_recipe
    # from scipy.optimize import least_squares

    # structure_path = Path(__file__).parents[2] / "data" / "Ni.cif"
    # profile_path = Path(__file__).parents[2] / "data" / "Ni.gr"
    # diffpycmi_recipe = make_recipe(str(structure_path), str(profile_path))
    # diffpycmi_recipe.free("scale")
    # least_squares(
    #     diffpycmi_recipe.residual, diffpycmi_recipe.values, x_scale="jac"
    # )
    # diffpycmi_recipe.plot_recipe()
