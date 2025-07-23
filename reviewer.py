import logging
import os
import re
from typing import Dict, Tuple, TypedDict, List

from langgraph.graph import END, StateGraph, START

from rtl_generator import RTLGenerator
from tb_generator import TBGenerator
from utils import add_lineno
from windows_cmd import run_cmd_command
from sim_judge import SimJudge

logger = logging.getLogger("root")
logger.info("Imported SimReviewer module")

def read_verilog_file(file_path):
    """
    Reads the entire content of a Verilog file into a string variable.

    Args:
        file_path (str): The path to the Verilog file.

    Returns:
        str: The content of the file, or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            verilog_code = f.read()
        return verilog_code
    except FileNotFoundError:
        logger.error(f"Error: The file '{file_path}' was not found.")
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred")
        return None

BENIGN_STDERRS = [
    r"^\S+:\d+: sorry: constant selects in always_\* processes are not currently supported \(all bits will be included\)\.$"
]

def stderr_all_lines_benign(stderr: str) -> bool:
    return all(
        any(re.match(pattern, line) for pattern in BENIGN_STDERRS)
        for line in stderr.splitlines()
    )

def check_rtl(rtl_path: str) -> Tuple[bool, str]:

    temp_folder_path = os.path.join(os.getcwd(), "temp")
    cmd = f"iverilog -t null -Wall -Winfloop -Wno-timescale -g2012 -o {temp_folder_path} {rtl_path}"

    sim_output = run_cmd_command(cmd)

    is_pass = (
        sim_output["success"]
        and "syntax error" not in sim_output["stdout"]
        and (
            sim_output["stderr"] == ""
            or stderr_all_lines_benign(sim_output["stderr"])
        )
    )
    logger.info(f"Syntax check is_pass: {is_pass}")
    logger.info(f"STDOUT: {sim_output['stdout']}")
    logger.info(f"STDERR: {sim_output['stderr']}")
    logger.info(f"RETURN: {sim_output['returncode']}")
    return is_pass, sim_output

def sim_review_mismatch_cnt(stdout: str) -> int:
    mismatch_cnt = 0
    if "SIMULATION FAILED" in stdout:
        mismatch_lines = []
        for line in stdout.strip().split('\n'):
            if line.startswith("Mismatch"):
                mismatch_lines.append(line)
        mismatch_cnt = len(mismatch_lines)
    return mismatch_cnt

def sim_review_get_mismatch_lines(stdout: str) -> List[str]:
    if "SIMULATION FAILED" in stdout:
        mismatch_lines = []
        for line in stdout.strip().split('\n'):
            if line.startswith("Mismatch"):
                mismatch_lines.append(line)
        return mismatch_lines
    else:
        return []
def sim_review_get_warning_lines(stdout: str) -> List[str]:
    mismatch_lines = []
    for line in stdout.strip().split('\n'):
        if line.startswith("WARNING"):
            mismatch_lines.append(line)
    return mismatch_lines

def sim_review(
    output_dir_per_run: str,
) -> Tuple[bool, int, str]:
    rtl_path = os.path.join(output_dir_per_run, "rtl.sv")
    vvp_name = os.path.join(output_dir_per_run, "sim_output.vvp")
    tb_path = os.path.join(output_dir_per_run, "tb.sv")

    if os.path.isfile(vvp_name):
        os.remove(vvp_name)

    cmd = "iverilog -Wall -Winfloop -Wno-timescale -g2012 -o {} {} {}&&vvp -n {}".format(
        vvp_name, tb_path, rtl_path, vvp_name
    )

    sim_output = run_cmd_command(cmd)

    is_pass = (
        sim_output["success"]
        and "SIMULATION PASSED" in sim_output["stdout"]
        and (
            sim_output["stderr"] == ""
            or stderr_all_lines_benign(sim_output["stderr"])
        )
    )
    mismatch_cnt = sim_review_mismatch_cnt(sim_output["stdout"])
    logger.info(
        f"Simulation is_pass: {is_pass}, mismatch_cnt: {mismatch_cnt}"
    )
    logger.info(f"STDOUT: {sim_output['stdout']}")
    logger.info(f"STDERR: {sim_output['stderr']}")
    logger.info(f"RETURN: {sim_output['returncode']}")

    return is_pass, mismatch_cnt, sim_output

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        error : Binary flag for control flow to indicate whether test error was tripped
        messages : With user question, error messages, reasoning
        generation : Code solution
        iterations : Number of tries
    """

    error: bool
    sim_output: Dict
    mismatch_cnt: int
    iterations: int

class SimReviewer:

    def __init__(self, input_spec, output_dir_per_run, max_iterations):


        self.input_spec = input_spec
        self.output_dir_per_run = output_dir_per_run
        self.max_iterations = max_iterations

        builder = StateGraph(GraphState)

        # Define the nodes
        builder.add_node("rtl_code_check", self.rtl_code_check)  # check code
        builder.add_node("rtl_code_fix", self.rtl_code_fix)  # check code
        builder.add_node("tb_code_check", self.tb_code_check)  # check code
        builder.add_node("tb_code_fix", self.tb_code_fix)  # check code
        builder.add_node("mismatch_check", self.mismatch_check)  # check code
        builder.add_node("mismatch_fix", self.mismatch_fix)  # check code
        builder.add_node("proceed_to_tb", self.proceed_to_tb)
        builder.add_node("proceed_to_mismatch", self.proceed_to_mismatch)

        # Build graph
        builder.add_edge(START, "rtl_code_check")

        builder.add_conditional_edges(
            "rtl_code_check",
            self.check_error_flag_iterations,
            {
                "end": END,
                "fix": "rtl_code_fix",
                "forward": "proceed_to_tb"
            },
        )
        builder.add_edge("rtl_code_fix", "rtl_code_check")
        builder.add_edge("proceed_to_tb", "tb_code_check")

        builder.add_conditional_edges(
            "tb_code_check",
            self.check_error_flag_iterations,
            {
                "end": END,
                "fix": "tb_code_fix",
                "forward": "proceed_to_mismatch"
            },
        )
        builder.add_edge("tb_code_fix", "tb_code_check")
        builder.add_edge("proceed_to_mismatch", "mismatch_check")

        builder.add_conditional_edges(
            "mismatch_check",
            self.check_error_flag_iterations,
            {
                "end": END,
                "fix": "mismatch_fix",
                "forward": END
            },
        )
        builder.add_edge("mismatch_fix", "mismatch_check")

        self.graph = builder.compile()

        logger.info("SimReviewer initialized.")

    def write_output(self, content: str, file_name: str) -> None:
        assert self.output_dir_per_run
        with open(os.path.join(self.output_dir_per_run, file_name), "w") as f:
            f.write(content)

    ### Nodes
    def rtl_code_check(self, state: GraphState):
        """
        Check code

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, error
        """

        logger.info("---CHECKING RTL CODE---")

        rtl_path = os.path.join(self.output_dir_per_run, "rtl.sv")

        try:
            is_pass, sim_output = check_rtl(rtl_path)
        except Exception as e:
            logger.info("---RTL CHECK FUNCTION FAILED---")
            logger.exception("Here is the error message")
            return {
                "error": True,
                "sim_output": {},
                "iterations": state["iterations"] + 1
            }

        return {
            "error": not is_pass,
            "sim_output": sim_output,
            "iterations": state["iterations"] + 1
        }
    
    def rtl_code_fix(self, state: GraphState):
        """
        Check code

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, error
        """

        logger.info("---FIXING RTL CODE---")

        rtl_path = os.path.join(self.output_dir_per_run, "rtl.sv")
        tb_path = os.path.join(self.output_dir_per_run, "tb.sv")
        if_path = os.path.join(self.output_dir_per_run, "if.sv")

        failure_string = f"""

----- IMPORTANT HINT FROM PREVIOUS RUN -------

A previous run with generated code for this specification failed in simulation. Keep this in mind when generating the new code for the RTL design:
<previous_code - rtl.sv>
{add_lineno(read_verilog_file(rtl_path))}
</previous_code>
<failed_sim_log>
{state["sim_output"]}
</failed_sim_log>
"""
        try:
            self.rtl_gen = RTLGenerator()
            rtl_code = self.rtl_gen.chat(
                input_spec=self.input_spec,
                testbench=read_verilog_file(tb_path),
                interface=read_verilog_file(if_path),
                failure_entry=failure_string
            )
            self.write_output(rtl_code, "rtl.sv")
        except Exception as e:
            logger.info("---RTL FIX FUNCTION FAILED---")
            logger.exception("Here is the error message")
            return {
                "error": True,
                "sim_output": {},
                "iterations": state["iterations"]
            }
        
        return {
            "error": False,
            "sim_output": {},
            "iterations": state["iterations"]
        }
    
    def tb_code_check(self, state: GraphState):
        """
        Check code

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, error
        """

        logger.info("---CHECKING TB CODE---")

        try:
            is_pass, _, sim_output = sim_review(self.output_dir_per_run)
        except Exception as e:
            logger.info("---TB CHECK FUNCTION FAILED---")
            logger.exception("Here is the error message")
            return {
                "error": True,
                "sim_output": {},
                "iterations": state["iterations"] + 1
            }
        
        return {
            "error": not (sim_output["success"] and sim_output["stderr"] == ""), # Moving forward if execution works without any problem, logic check will happen in mismatch
            "sim_output": sim_output,
            "iterations": state["iterations"] + 1
        }
    
    @staticmethod
    def explain_result(result):
        """
        Converts a result dictionary into a natural language explanation.

        Args:
            result (dict): The dictionary with command execution results.
            preprocess_stdout_function (callable, optional): A function to preprocess
                                                            the stdout list.
                                                            Defaults to None.
        Returns:
            str: A natural language explanation of the command's outcome.
        """
        explanation_parts = []

        if result['returncode'] == 0:
            explanation_parts.append("The command executed successfully.")
        else:
            explanation_parts.append(f"The command failed with a return code of {result['returncode']}.")

        if result["error_message"] is not None:
            explanation_parts.append(f"An error occurred during the command execution phase: \"{result['error_message']}\".")

        # 3. Stderr Check (iVerilog specific)
        if result["stderr"] != "":
            explanation_parts.append("iVerilog reported some error statements during execution, indicated by messages in the standard error stream.")
            explanation_parts.append(f"Standard error output:\n---\n{result['stderr']}\n---")

        # 4. Stdout Check (preprocessed problematic parts)
        # Ensure preprocess_stdout_function is provided and callable
        mismatch_lines = sim_review_get_mismatch_lines(result["stdout"])
        if mismatch_lines:
            explanation_parts.append("The simulation reported the following mismatches when running the simulation with the given testbench and RTL code:")
            for i, issue in enumerate(mismatch_lines):
                explanation_parts.append(f"- {issue}")
        
        warning_lines = sim_review_get_mismatch_lines(result["stdout"])
        if warning_lines:
            explanation_parts.append("The simulation reported the following WARNINGS when running the simulation with the given testbench and RTL code:")
            for i, issue in enumerate(warning_lines):
                explanation_parts.append(f"- {issue}")

        return "\n".join(explanation_parts)

    def tb_code_fix(self, state: GraphState):
        """
        Check code

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, error
        """

        logger.info("---FIXING TB CODE---")

        rtl_path = os.path.join(self.output_dir_per_run, "rtl.sv")
        tb_path = os.path.join(self.output_dir_per_run, "tb.sv")

        sim_output = self.explain_result(state["sim_output"])

        failure_string = f"""

----- IMPORTANT HINT FROM PREVIOUS RUN -------

A previous run with generated code for this specification failed in simulation. Keep this in mind when generating the new code for the Testbench/ Interface Design :
<previous_code - rtl.sv>
{add_lineno(read_verilog_file(rtl_path))}
</previous_code>
<previous_tb - tb.sv>
{add_lineno(read_verilog_file(tb_path))}
</previous_tb>
<failed_sim_log>
{sim_output}
</failed_sim_log>
"""

        try:
            self.tb_gen = TBGenerator()

            testbench, interface = self.tb_gen.chat(self.input_spec, failure_entry=failure_string)

            self.write_output(testbench, "tb.sv")
            self.write_output(interface, "if.sv")

        except Exception as e:
            logger.info("---TB FIX FUNCTION FAILED---")
            logger.exception("Here is the error message")
            return {
                "error": True,
                "sim_output": {},
                "iterations": state["iterations"]
            }
        
        return {
            "error": False,
            "sim_output": {},
            "iterations": state["iterations"]
        }
    
    def mismatch_check(self, state: GraphState):
        """
        Check code

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, error
        """

        logger.info("---MISMATCH_CHECK---")

        try:
            is_pass, mismatch_cnt, sim_output = sim_review(self.output_dir_per_run)
        except Exception as e:
            logger.info("---MISMATCH CHECK FUNCTION FAILED---")
            logger.exception("Here is the error message")
            return {
                "error": True,
                "sim_output": {},
                "mismatch_cnt" : 0,
                "iterations": state["iterations"] + 1
            }
        
        return {
            "error": (not is_pass) | mismatch_cnt !=0,
            "sim_output": sim_output,
            "mismatch_cnt" : mismatch_cnt,
            "iterations": state["iterations"] + 1
        }
    
    def mismatch_fix(self, state: GraphState):
        """
        Check code

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, error
        """

        logger.info("---MISMATCH FIX---")

        rtl_path = os.path.join(self.output_dir_per_run, "rtl.sv")
        tb_path = os.path.join(self.output_dir_per_run, "tb.sv")
        if_path = os.path.join(self.output_dir_per_run, "if.sv")

        judge = SimJudge()

        sim_output = self.explain_result(state["sim_output"])

        rtl_needs_fix, tb_needs_fix, reasoning = judge.chat(
            input_spec=self.input_spec, 
            failed_sim_log=sim_output, 
            failed_rtl=add_lineno(read_verilog_file(rtl_path)),
            failed_testbench=add_lineno(read_verilog_file(tb_path))
        )
        logger.info(f"\nResult: TB Needs Fix = {tb_needs_fix}")
        logger.info(f"\nResult: RTL Needs Fix = {rtl_needs_fix}")
        logger.info(f"Reasoning:\n{reasoning}")

        if tb_needs_fix:

            failure_string = f"""

----- IMPORTANT HINT FROM PREVIOUS RUN -------

A previous run with generated code for this specification failed in simulation. Keep this in mind when generating the new code for the Testbench/ Interface Design :
<previous_code - rtl.sv>
{add_lineno(read_verilog_file(rtl_path))}
</previous_code>
<previous_tb - tb.sv>
{add_lineno(read_verilog_file(tb_path))}
</previous_tb>
<failed_sim_log>
{sim_output}
</failed_sim_log>
<Output by a reasoning agent>
{reasoning}
</Output by a reasoning agent>
"""
            try:
                self.tb_gen = TBGenerator()
                testbench, interface = self.tb_gen.chat(self.input_spec, failure_entry=failure_string)
                self.write_output(testbench, "tb.sv")
                self.write_output(interface, "if.sv")

            except Exception as e:
                logger.info("---TB FIX FUNCTION IN MISMATCH FIX FAILED---")
                logger.exception("Here is the error message")
                return {
                    "error": True,
                    "sim_output": {},
                    "mismatch_cnt" : 0,
                    "iterations": state["iterations"]
                }
            

        if rtl_needs_fix:
            failure_string = f"""

----- IMPORTANT HINT FROM PREVIOUS RUN -------

A previous run with generated code for this specification failed in simulation. Keep this in mind when generating the new code for the Testbench/ Interface Design :
<previous_code - rtl.sv>
{add_lineno(read_verilog_file(rtl_path))}
</previous_code>
<previous_tb - tb.sv>
{add_lineno(read_verilog_file(tb_path))}
</previous_tb>
<failed_sim_log>
{sim_output}
</failed_sim_log>
<Output by a reasoning agent>
{reasoning}
</Output by a reasoning agent>
"""

            try:
                self.rtl_gen = RTLGenerator()
                rtl_code = self.rtl_gen.chat(
                    input_spec=self.input_spec,
                    testbench=read_verilog_file(tb_path),
                    interface=read_verilog_file(if_path),
                    failure_entry=failure_string
                )
                self.write_output(rtl_code, "rtl.sv")
            except Exception as e:
                logger.info("---RTL FIX FUNCTION IN MISMATCH FIX FAILED---")
                logger.exception("Here is the error message")
                return {
                    "error": True,
                    "sim_output": {},
                    "mismatch_cnt" : 0,
                    "iterations": state["iterations"]
                }

        if not (tb_needs_fix | rtl_needs_fix):
            return {
                "error": True,
                "sim_output": {},
                "mismatch_cnt" : 0,
                "iterations": state["iterations"]
            }
    
    def proceed_to_tb(self, state: GraphState):
        return {
            "error": False,
            "sim_output": {},
            "mismatch_cnt" : 0,
            "iterations": 0
        }
    
    def proceed_to_mismatch(self, state: GraphState):
        return {
            "error": False,
            "sim_output": {},
            "mismatch_cnt" : 0,
            "iterations": 0
        }

    ### Conditional edges


    def check_error_flag_iterations(self, state: GraphState):
        """
        Determines whether to finish.

        Args:
            state (dict): The current graph state

        Returns:
            str: Next node to call
        """
        if not state["error"]:
            logger.info("CHECK PASSED! MOVING FORWARD")
            return "forward"
        else:
            logger.info("CHECK NOT PASSED!")
            if state["iterations"] >= self.max_iterations:
                logger.info("---Iteration Limit Reached---")
                return "end"
        logger.info("Moving to FIX")
        return "fix"
    
    def invoke_rag(self):
        # Run
        inputs = {
            "error": False,
            "sim_output": {},
            "iterations": 0
        }

        for output in self.graph.stream(inputs):
            for key, value in output.items():
                logger.info(f"Node '{key}':")
            logger.info("\n---\n")

        # Final generation

        if value["error"]:
            logger.error("RTL Generation completed with errors")
        else:
            logger.info("RTL Generation completed successfully!")

        return value
    

# input_spec = """

# **Simple Verilog Design: 4-Bit Ripple-Carry Adder**

# **1. Design Name:** `ripple_carry_adder_4bit`

# **2. Purpose:** To demonstrate fundamental digital logic design principles, module instantiation, and basic combinational circuit behavior. Specifically, it will add two 4-bit unsigned binary numbers and produce a 4-bit sum and a 1-bit carry-out.

# **3. Functionality:**
#     * Takes two 4-bit input binary numbers (A and B).
#     * Takes a 1-bit carry-in (Cin).
#     * Produces a 4-bit sum (S).
#     * Produces a 1-bit carry-out (Cout).
#     * Implements a ripple-carry adder structure using four instantiated 1-bit full adder modules.

# **4. Module Structure:**

# *   **Top-Level Module:** `ripple_carry_adder_4bit`
#     *   Instantiates four `full_adder_1bit` modules.
#     *   Connects the carry-out of one full adder to the carry-in of the next.

# *   **Sub-Module (Instantiated):** `full_adder_1bit`
#     *   Implements the logic for a single 1-bit full adder.

# **5. Inputs:**

# *   `A` : `input [3:0] A;` (4-bit unsigned number)
# *   `B` : `input [3:0] B;` (4-bit unsigned number)
# *   `Cin`: `input Cin;` (1-bit carry-in)

# **6. Outputs:**

# *   `S`   : `output [3:0] S;` (4-bit sum)
# *   `Cout`: `output Cout;` (1-bit final carry-out)

# **7. Internal Signals (Wires):**

# *   `carry_intermediate`: `wire [3:1] carry_intermediate;` (3-bit wire to connect carry-out of FA0 to FA1, FA1 to FA2, FA2 to FA3)
#     *   `carry_intermediate[1]` connects C1 from FA0 to Cin of FA1.
#     *   `carry_intermediate[2]` connects C2 from FA1 to Cin of FA2.
#     *   `carry_intermediate[3]` connects C3 from FA2 to Cin of FA3.

# **8. Block Diagram (Conceptual):**

# ```
#      Cin ----> [FA0] A[0], B[0] ----> S[0], C1
#                       |
#                       v
#                      C1 ----> [FA1] A[1], B[1] ----> S[1], C2
#                                     |
#                                     v
#                                    C2 ----> [FA2] A[2], B[2] ----> S[2], C3
#                                                  |
#                                                  v
#                                                 C3 ----> [FA3] A[3], B[3] ----> S[3], Cout
# ```

# **9. Behavioral/Structural Description (Verilog-like):**

# *   **`full_adder_1bit` Module Logic:**
#     *   `sum = A ^ B ^ Cin;`
#     *   `carry_out = (A & B) | (Cin & (A ^ B));`

# *   **`ripple_carry_adder_4bit` Module Structure:**
#     *   Instantiate `full_adder_1bit` for bit 0:
#         `fa0 ( .A(A[0]), .B(B[0]), .Cin(Cin), .S(S[0]), .Cout(carry_intermediate[1]) );`
#     *   Instantiate `full_adder_1bit` for bit 1:
#         `fa1 ( .A(A[1]), .B(B[1]), .Cin(carry_intermediate[1]), .S(S[1]), .Cout(carry_intermediate[2]) );`
#     *   Instantiate `full_adder_1bit` for bit 2:
#         `fa2 ( .A(A[2]), .B(B[2]), .Cin(carry_intermediate[2]), .S(S[2]), .Cout(carry_intermediate[3]) );`
#     *   Instantiate `full_adder_1bit` for bit 3:
#         `fa3 ( .A(A[3]), .B(B[3]), .Cin(carry_intermediate[3]), .S(S[3]), .Cout(Cout) );`

# **10. Design Style:** Primarily structural (instantiating sub-modules), with behavioral (assign statements or logic gates) for the `full_adder_1bit` sub-module.

# **11. Constraints/Assumptions:**
#     *   Numbers are unsigned.
#     *   Combinational logic (no clocks, no sequential elements).
#     *   Target technology: Generic ASIC or FPGA (logic synthesis tool will map to gates).

# """

# sim_reviewer = SimReviewer(
#     input_spec=input_spec,
#     output_dir_per_run=r"C:\Users\Paulson\Documents\Projects\Python\99_Scratch\verilog\output\test_1",
#     max_iterations=3
# )

# sim_reviewer.invoke_rag()