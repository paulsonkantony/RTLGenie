import logging
from typing import Dict, List, Tuple

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

# Assuming these are defined elsewhere and correctly imported
from prompts import RTL_4_SHOT_EXAMPLES # Potentially useful for examples in the prompt, but not directly used in the judge chain logic
from utils import add_lineno # Still unused, can be removed if not used elsewhere in the file
from llm import llm # Ensure llm is an initialized LangChain LLM object

import logger_config
logger = logging.getLogger("root")
logger.info("Imported Sim Judge module") # Updated log message

# --- Pydantic Model for RTL Judge ---

class JudgeFormat(BaseModel):
    """
    Defines the structured output format for the RTL judgment.
    """
    reasoning: str = Field(
        description="All reasoning steps and advices to fix the code based on the simulation log and specification."
    )
    rtl_needs_fix: bool = Field(
        description="Flag indicating that the RTL module must be modified to meet the specifications or fix errors."
    )
    tb_needs_fix: bool = Field(
        description="Flag indicating that the testbench must be modified to meet the specifications or fix errors."
    )

# --- RTL Judge Function ---

def get_judge(llm):
    """
    Creates a LangChain chain for judging SystemVerilog RTL.

    Args:
        llm: The Language Model instance (e.g., ChatOpenAI).

    Returns:
        A LangChain Runnable that takes 'input_spec', 'failed_sim_log',
        'failed_rtl', 'failed_testbench' as input and returns an RTLJudgeFormat object.
    """

    structured_judge = llm.with_structured_output(JudgeFormat)

    system_prompt = """
You are an expert in RTL verification. Your task is to analyze failed simulation logs,
the original design specification, and the current RTL and Testbench code to determine if
the RTL or the testbench needs modification **strictly based on the provided input specification**.
"""

    messages = [
        ("system", system_prompt),
        ("human", """
A simulation has failed for the RTL (Register Transfer Level) module and its corresponding testbench. Your task is to evaluate whether the RTL module or the testbench requires modifications based on the provided input specification and the details from the failed simulation log.


### **1. Mandatory TB Input Checks (FIRST PRIORITY)**
**A. Input Specification Compliance**  
   - ✔ Verify ALL TB-driven inputs match spec **widths/datatypes** exactly  
   - ✔ Confirm TB applies **valid input combinations** per spec constraints  
   - *TB bug if*: Input violates spec range/enumerations (e.g., driving 5-bit to 4-bit port)

**B. Expected Value Calculation**  
   - ✔ TB must compute expected outputs **exactly as defined by spec equations**  
   - ✔ For arithmetic operations, verify overflow/underflow handling matches spec  
   - *TB bug if*: Reference calculation ≠ spec behavior (e.g., `>>4` instead of `>15` for carry)

**C. Timing & Sequencing**  
   - ✔ For combinational designs: TB must allow **sufficient propagation delay** before sampling  
   - ✔ For sequential designs: Inputs must change at **mid-cycle** (not clock edges)  
   - *TB bug if*: Sampling too early or inputs changing at active clock edges

---

### **2. RTL Spec Compliance Checks**
**A. Functional Correctness**  
   - ✔ Outputs must match spec **truth tables/equations** for given inputs  
   - *RTL bug if*: Output ≠ spec-defined result (e.g., sum incorrect per adder logic)

**B. Structural Compliance**  
   - ✔ Verify submodule connections match spec **hierarchy and wiring**  
   - *RTL bug if*: Incorrect port mapping (e.g., carry chain miswired)

**C. Bit-width Handling**  
   - ✔ Check all operations respect spec-defined **bit widths**  
   - *RTL bug if*: Missing overflow handling (e.g., no carry generation)

---

### **3. Corner Case Validation**
**A. Boundary Conditions**  
   - ✔ Verify behavior at **spec-defined edge cases** (e.g., max+1 addition)  
   - *RTL bug if*: Fails spec-mandated edge cases  
   - *TB bug if*: Doesn't test required boundary values

---

### **Decision Protocol**
- Set `tb_needs_fix = True` if ANY input check fails:  
  1. Input values/widths violate spec  
  2. Expected value calculation ≠ spec  
  3. Timing violates combinational/sequential rules  

- Set `rtl_needs_fix = True` ONLY if:  
  1. All TB checks pass but RTL output ≠ spec  
  2. Structural implementation violates spec  

---

### **Output Requirements**
1. Assign `rtl_needs_fix`/`tb_needs_fix` as booleans  
2. **Reasoning must**:  
   - First analyze TB input compliance  
   - Reference SPEC sections by name/number  
   - Quote exact code vs spec mismatch  
3. **Fix Suggestions**:  
   - For TB: Provide corrected calculations/timing  
   - For RTL: Highlight non-compliant logic

**Input Sections**:

<input_spec>
{input_spec}
</input_spec>
<failed_sim_log>
{failed_sim_log}
</failed_sim_log>
<failed_rtl>
{failed_rtl}
</failed_rtl>
<failed_testbench>
{failed_testbench}
</failed_testbench>


"""
        ),
    ]

    judge_prompt = ChatPromptTemplate.from_messages(messages)

    return  judge_prompt | structured_judge


class SimJudge:
    """
    Judges whether a SystemVerilog RTL design needs to be fixed based on simulation results.
    """
    def __init__(self):
        """
        Initializes the SimJudge.
        """
        logger.info("SimJudge initialized.")

    def chat(
        self,
        input_spec: str,
        failed_sim_log: str,
        failed_rtl: str,
        failed_testbench: str,
    ) -> Tuple[str, bool]:
        """
        Invokes the LLM to judge whether the RTL needs to be fixed
        based on the simulation log, input specification, failed RTL, and failed testbench.

        Args:
            input_spec (str): The natural language specification for the module.
            failed_sim_log (str): The log output from the failed simulation.
            failed_rtl (str): The RTL code that caused the simulation to fail.
            failed_testbench (str): The testbench code used in the failed simulation (for context).

        Returns:
            Tuple[str, bool]: A tuple containing the reasoning string and
                             a boolean indicating if the RTL needs a fix.
        """
        
        llm_chain = get_judge(llm) # Get the LangChain runnable for the RTL judge

        # Prepare the input dictionary for the LLM chain
        chain_inputs = {
            "input_spec": input_spec,
            "failed_sim_log": failed_sim_log,
            "failed_rtl": failed_rtl,
            "failed_testbench": failed_testbench,
        }

        # Limit the length of the previews for readability in logs
        input_spec_display = (input_spec[:50] + '...') if len(input_spec) > 50 else input_spec
        sim_log_display = (failed_sim_log[:50] + '...') if len(failed_sim_log) > 50 else failed_sim_log
        rtl_display = (failed_rtl[:50] + '...') if len(failed_rtl) > 50 else failed_rtl
        tb_display = (failed_testbench[:50] + '...') if len(failed_testbench) > 50 else failed_testbench # Keeping this for context in the prompt

        logger.debug(f"Invoking LLM with chain inputs for SimJudge: "
                    f"input_spec='{input_spec_display}', "
                    f"failed_sim_log='{sim_log_display}', "
                    f"failed_rtl='{rtl_display}', "
                    f"failed_testbench='{tb_display}'")

        response: JudgeFormat = llm_chain.invoke(chain_inputs)

        # Log the LLM's response for debugging and transparency
        logger.info("SimJudge LLM Response received.")
        logger.info(f"RTL Needs Fix: {response.rtl_needs_fix}")
        logger.info(f"TB Needs Fix: {response.tb_needs_fix}")
        logger.info(f"Reasoning:\n{response.reasoning}")

        return response.rtl_needs_fix, response.tb_needs_fix, response.reasoning