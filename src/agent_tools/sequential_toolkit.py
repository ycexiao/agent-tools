from pathlib import Path
import re
import json
import threading
from typing import Literal

from requests import session
from agent_tools.pdfadapter import PDFAdapter
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


class SequentialPDFFitRunner:
    def __init__(self):
        self.input_files_known = []
        self.input_files_completed = []
        self.input_files_running = []
        self.adapter = PDFAdapter()

    def load_inputs(
        self,
        input_data_dir,
        structure_path,
        output_result_dir="results",
        filename_order_pattern=r"(\d+)K\.gr",
        refine_variable_names=None,
        initial_variable_values=None,
        xmin=None,
        xmax=None,
        dx=None,
        qmin=None,
        qmax=None,
    ):
        self.inputs = {
            "input_data_dir": input_data_dir,
            "structure_path": structure_path,
            "output_result_dir": output_result_dir,
            "filename_order_pattern": filename_order_pattern,
            "xmin": xmin,
            "xmax": xmax,
            "dx": dx,
            "qmin": qmin,
            "qmax": qmax,
            "refine_variable_names": refine_variable_names or [],
            "initial_variable_values": initial_variable_values or {},
        }

    def check_for_new_data(self):
        input_data_dir = self.inputs["input_data_dir"]
        filename_order_pattern = self.inputs["filename_order_pattern"]
        files = [file for file in Path(input_data_dir).glob("*")]
        sorted_file = sorted(
            files,
            key=lambda file: int(
                re.findall(filename_order_pattern, file.name)[0]
            ),
        )
        if (
            self.input_files_known
            != sorted_file[: len(self.input_files_known)]
        ):
            raise RuntimeError(
                "Wrong order to run sequential toolset is detected. "
                "This is likely due to files appearing in the input directory "
                "in the wrong order. Please restart the sequential toolset."
            )
        if self.input_files_known == sorted_file:
            return
        self.input_files_known = sorted_file
        self.input_files_running = [
            f
            for f in self.input_files_known
            if f not in self.input_files_completed
        ]
        print(f"{[str(f) for f in self.input_files_running]} detected.")

    def set_start_input_file(
        self, input_filename, input_filename_to_result_filename
    ):
        input_file_path = Path(input_filename)
        if input_file_path not in self.input_files_known:
            raise ValueError(
                f"Input file {input_filename} not found in known input files."
            )
        start_index = self.input_files_known.index(input_file_path)
        self.input_files_completed = self.input_files_known[:start_index]
        self.input_files_running = self.input_files_known[start_index:]
        last_result_file = input_filename_to_result_filename(
            self.input_files_completed[-1]
        )
        last_result_variables_values = json.load(open(last_result_file, "r"))[
            "variables"
        ]
        last_result_variables_values = {
            name: pack["value"]
            for name, pack in last_result_variables_values.items()
        }
        self.last_result_variables_values = last_result_variables_values

    def start_one_round(self):
        self.check_for_new_data()
        xmin = self.inputs["xmin"]
        xmax = self.inputs["xmax"]
        dx = self.inputs["dx"]
        qmin = self.inputs["qmin"]
        qmax = self.inputs["qmax"]
        structure_path = self.inputs["structure_path"]
        output_result_dir = self.inputs["output_result_dir"]
        initial_variable_values = self.inputs["initial_variable_values"]
        refine_variable_names = self.inputs["refine_variable_names"]
        if not self.input_files_running:
            return None
        for input_file in self.input_files_running:
            self.adapter.init_profile(
                str(input_file),
                xmin=xmin,
                xmax=xmax,
                dx=dx,
                qmin=qmin,
                qmax=qmax,
            )
            self.adapter.init_structures(structure_path)
            self.adapter.init_contribution()
            self.adapter.init_recipe()
            if not hasattr(self, "last_result_variables_values"):
                self.last_result_variables_values = initial_variable_values
            self.adapter.set_initial_variable_values(
                self.last_result_variables_values
            )
            if refine_variable_names is None:
                refine_variable_names = list(initial_variable_values.keys())
            self.adapter.refine_variables(refine_variable_names)
            results = self.adapter.save_results(
                filename=str(
                    Path(output_result_dir) / f"{input_file.stem}_result.json"
                ),
                mode="dict",
            )
            self.last_result_variables_values = {
                name: pack["value"]
                for name, pack in results["variables"].items()
            }
            self.input_files_completed.append(input_file)
            print(f"Completed processing {input_file.name}.")
        self.input_files_running = []

    def start(self, mode: Literal["batch", "stream"]):
        if mode == "batch":
            self.start_one_round()
        elif mode == "stream":
            stop_event = threading.Event()
            session = PromptSession()

            def stream_loop():
                while not stop_event.is_set():
                    self.start_one_round()
                    stop_event.wait(1)  # Check for new data every 1 second

            def input_thread():
                with patch_stdout():
                    print("=== COMMANDS ===")
                    print("Type STOP to exit")
                    print("================")
                    while not stop_event.is_set():
                        cmd = session.prompt("> ")
                        if cmd.strip() == "STOP":
                            stop_event.set()
                            print(
                                "Stopping the streaming sequential toolset..."
                            )
                        else:
                            print(
                                "Unrecognized input. Please type 'STOP' to end."
                            )

            input_thread = threading.Thread(target=input_thread)
            input_thread.start()
            fit_thread = threading.Thread(target=stream_loop)
            fit_thread.start()
            fit_thread.join()
            input_thread.join()
        else:
            raise ValueError(f"Unknown mode: {mode}")


if __name__ == "__main__":
    sts = SequentialPDFFitRunner()
    sts.load_inputs(
        input_data_dir="data/input_files",
        structure_path="data/Ni.cif",
        output_result_dir="data/results",
        filename_order_pattern=r"(\d+)K\.gr",
        refine_variable_names=[
            "a_1",
            "s0",
            "Uiso_0_1",
            "delta2_1",
            "qdamp",
            "qbroad",
        ],
        initial_variable_values={
            "s0": 0.4,
            "qdamp": 0.04,
            "qbroad": 0.02,
            "a_1": 3.52,
            "Uiso_0_1": 0.005,
            "delta2_1": 2,
        },
        xmin=1.5,
        xmax=25.0,
        dx=0.01,
        qmax=25,
        qmin=0.1,
    )
    sts.start(mode="stream")
