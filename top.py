import os
import sys
import logging
import traceback
from dataclasses import dataclass
from typing import List, TypedDict, Any, Dict, Tuple
from pprint import pprint

from tb_generator import TBGenerator
from rtl_generator import RTLGenerator
from reviewer import SimReviewer


import logger_config
logger = logging.getLogger("root")

from langgraph.graph import StateGraph, START, END

from llm import llm

import os
import shutil

def create_backup(backup_folder_name: str) -> None:
    """
    Copies the contents of './output', the folder 'log', and the file 'config.toml'
    into a new subfolder named 'backup_folder_name' within './output_backup'.

    Args:
        backup_folder_name: The name for the new subfolder within './output_backup'.
                            This subfolder will be created if it doesn't exist.
    """
    source_output_dir = "./output/test_0"
    source_log_dir = "./log"
    source_config_file = "./config.toml"
    base_backup_dir = "./output_backup"

    # Construct the full path for the new backup subfolder
    destination_backup_dir = os.path.join(base_backup_dir, backup_folder_name)

    print(f"--- Starting Backup Process ---")
    print(f"Target backup directory: {os.path.abspath(destination_backup_dir)}")

    try:
        # 1. Create the base backup directory if it doesn't exist
        os.makedirs(base_backup_dir, exist_ok=True)
        print(f"Ensured base backup directory exists: {os.path.abspath(base_backup_dir)}")

        # 2. Create the new specific backup subfolder
        os.makedirs(destination_backup_dir, exist_ok=True)
        print(f"Created new backup subfolder: {os.path.abspath(destination_backup_dir)}")

        # 3. Copy contents of "./output"
        if os.path.exists(source_output_dir):
            print(f"Copying contents of '{source_output_dir}'...")
            # shutil.copytree requires the destination directory to not exist
            # if we are copying the folder itself.
            # To copy *contents* into an existing destination, we copy it *into* the destination.
            # We want './output_backup/<name>/output/'
            shutil.copytree(source_output_dir, os.path.join(destination_backup_dir, os.path.basename(source_output_dir)), dirs_exist_ok=True)
            print(f"Successfully copied '{source_output_dir}'.")
        else:
            print(f"Warning: '{source_output_dir}' does not exist. Skipping.")

        # 4. Copy folder "log"
        if os.path.exists(source_log_dir):
            print(f"Copying folder '{source_log_dir}'...")
            # We want './output_backup/<name>/log/'
            shutil.copytree(source_log_dir, os.path.join(destination_backup_dir, os.path.basename(source_log_dir)), dirs_exist_ok=True)
            print(f"Successfully copied '{source_log_dir}'.")
        else:
            print(f"Warning: '{source_log_dir}' does not exist. Skipping.")

        # 5. Copy file "config.toml"
        if os.path.exists(source_config_file) and os.path.isfile(source_config_file):
            print(f"Copying file '{source_config_file}'...")
            # copy2 preserves metadata; destination is the directory where the file should go
            shutil.copy2(source_config_file, destination_backup_dir)
            print(f"Successfully copied '{source_config_file}'.")
        else:
            print(f"Warning: '{source_config_file}' does not exist or is not a file. Skipping.")

        print(f"\nBackup completed successfully to: {os.path.abspath(destination_backup_dir)}")

    except FileNotFoundError as e:
        print(f"Error: A required source path was not found. Details: {e}")
    except PermissionError as e:
        print(f"Error: Permission denied. Please check folder permissions. Details: {e}")
    except shutil.Error as e:
        print(f"Error during copy operation. Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during backup. Details: {e}")
    finally:
        print("--- Backup Process Finished ---")

class TopAgent: 

    def __init__(self):
        self.llm = llm
        self.output_path = os.path.join(os.getcwd(), "output")
        self.tb_gen: TBGenerator | None = None
        self.rtl_gen: RTLGenerator | None = None
        self.sim_reviewer: SimReviewer | None = None

    def set_output_path(self, output_path: str) -> None:
        self.output_path = output_path

    def write_output(self, content: str, file_name: str) -> None:
        assert self.output_dir_per_run
        with open(os.path.join(self.output_dir_per_run, file_name), "w") as f:
            f.write(content)

    def _run(self, spec):

        try:
            if os.path.exists(os.path.join(self.output_dir_per_run, "properly_finished.tag")):
                os.remove(os.path.join(self.output_dir_per_run, "properly_finished.tag"))

            self.rtl_gen = RTLGenerator()
            self.tb_gen = TBGenerator()
            self.sim_reviewer = SimReviewer(
                input_spec=spec,
                output_dir_per_run=self.output_dir_per_run,
                max_iterations=5
            )

            testbench, interface = self.tb_gen.chat(
                input_spec=spec
            )

            self.write_output(testbench, "tb.sv")
            self.write_output(interface, "if.sv")

            rtl_code = self.rtl_gen.chat(
                input_spec=spec,
                testbench=testbench,
                interface=interface
            )

            self.write_output(rtl_code, "rtl.sv")

            value = self.sim_reviewer.invoke_rag()

            final_result = True
            if value["error"]:
                final_result = False

            with open(f"{self.output_dir_per_run}/properly_finished.tag", "w") as f:
                if final_result:
                    f.write("1")
                else:
                    f.write(f"0\n{value}")

        except Exception:
            exc_info = sys.exc_info()
            traceback.print_exception(*exc_info)
            return False, f"Exception: {exc_info[1]}"

        return True, rtl_code

    def run(
        self,
        benchmark_type_name: str,
        task_id: str,
        spec: str,
    ) -> Tuple[bool, str]:

        self.output_dir_per_run = os.path.join(self.output_path, f"{benchmark_type_name}_{task_id}")
        os.makedirs(self.output_path, exist_ok=True)
        os.makedirs(self.output_dir_per_run, exist_ok=True)

        result = self._run(spec)
        
        return result
    
if __name__ == "__main__":
    obj = TopAgent()

    import tomllib

    def parse_toml_file(file_path):
        with open(file_path, "rb") as f:
            config = tomllib.load(f)
        return config
    config = parse_toml_file("config.toml")

    obj.run(
        benchmark_type_name="test",
        task_id=0,
        spec = config["SPEC"]["input_spec"]
    )

    create_backup(config["SPEC"]["name"])