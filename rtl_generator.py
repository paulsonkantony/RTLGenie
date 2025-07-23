import logging
from typing import Dict, List, Tuple

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

# Assuming these are defined elsewhere and correctly imported
from prompts import RTL_4_SHOT_EXAMPLES
from utils import add_lineno # Not used in optimized get_tb_writer
from llm import llm # Ensure llm is an initialized LangChain LLM object

import logger_config
logger = logging.getLogger("root")
logger.info("Imported RTL Generator module")

# --- Pydantic Model ---

class RTLOutputFormat(BaseModel):
    """
    Defines the structured output format for the testbench generation.
    """
    reasoning: str = Field(
        description="All reasoning steps and advices to avoid syntax error"
    )
    module: str = Field(
        description="Pure SystemVerilog code of the module"
                    "This should be error-free and ready for output to .SV file that can be run using a verilog simulator"
    )

# --- RTL Writer Function ---

def get_rtl_writer(llm):
    """
    Creates a LangChain chain for generating SystemVerilog RTL.

    Args:
        llm: The Language Model instance (e.g., ChatOpenAI).

    Returns:
        A LangChain Runnable that takes 'input_spec', 'examples_prompt',
        'display_prompt' as input and returns a RTLOutputFormat object.
    """

    structured_rtl_writer = llm.with_structured_output(RTLOutputFormat)

    system_prompt = """
You are an expert in RTL design. You can always write SystemVerilog code with no syntax errors and always reach correct functionality.
"""

    messages = [
        ("system", system_prompt),
        ("human", """
Please write a module in SystemVerilog RTL language based on the given natural language specification. 
Your response should include reasoning steps in natural language to achieve the implementation. Additionally, provide advice to avoid syntax errors.

Key Points:
- A SystemVerilog RTL module starts with the keyword 'module' followed by the module name and ends with 'endmodule'.
- Ensure the module interface matches the provided module_interface or input_spec exactly, including names and types of input/output ports.

[Hints]:
- For implementing a Karnaugh map (K-map), think step by step. Carefully analyze how the K-map in input_spec specifies the order of the inputs.
- Remember that x[i] in x[N:1] corresponds to x[i-1] in x[N-1:0].
- Identify inputs corresponding to output=1, 0, and don't-care for each case.

Important Syntax Notes:
- For a signal defined as "logic x[M:N]" where M > N, do NOT select bits reversely (e.g., x[1:2]). Use concatenation instead, like {{x[1], x[2]}}.
- Declare all ports and signals as logic.
- Not all sequential logic needs to reset to 0 when reset is asserted; those without reset should be initialized to a known value using an initial block.
- For combinational logic, use always @(*) without specifying the sensitivity list.
- Avoid using the 'inside' operator and the 'unique' or 'unique0' keywords in RTL code.
- If any submodules are described, provide their full definitions in the same file.
         
Other Requirements:
1. Do not use state_t to define the parameter. Use `localparam` or use 'reg' or 'logic' for signals as registers or Flip-Flops.
2. Declare all ports and signals as logic.
3. Not all sequential logic needs to be reset to 0 when reset is asserted; those without reset should be initialized to a known value with an initial block instead of being X.
4. For combinational logic with an always block, do not explicitly specify the sensitivity list; instead, use always @(*).
5. NEVER USE the 'inside' operator in RTL code. Code like 'state inside {{STATE_B, STATE_C, STATE_D}}' should NOT be used.
6. Never USE 'unique' or 'unique0' keywords in RTL code. Code like 'unique case' should NOT be used.
7. If any submodules are described, the full definition of the submodules must also be generated in the same file.

<input_spec>
{input_spec}
</input_spec>

The module interface is given below:
<module_interface>
{module_interface}
</module_interface>

Another agent has generated a testbench based on the given input_spec:
<testbench>
{testbench}
</testbench>
         
-----------------------------------------

{failure_entry} 
         
-----------------------------------------

{examples_prompt}
                
"""
        ),
    ]

    rtl_gen_prompt = ChatPromptTemplate.from_messages(messages)

    return  rtl_gen_prompt | structured_rtl_writer


class RTLGenerator:
    """
    Generates SystemVerilog RTL using an LLM,
    with capabilities for iterative refinement based on failed simulations.
    """
    def __init__(self):
        """
        Initializes the RTLGenerator.
        """

        self.generated_tb: str | None = None
        self.generated_if: str | None = None

        logger.info("RTLGenerator initialized.")

    def chat(
            self,
            input_spec: str,
            testbench: str,
            interface: str,
            failure_entry = ""
        ) -> str:
        """
        Invokes the LLM to generate a testbench and interface based on the input specification
        and accumulated failed trial history.

        Args:
            input_spec (str): The natural language specification for the module to be tested.

        Returns:
            Tuple[str, str]: A tuple containing the generated testbench code and
                             the generated module interface code.
        """
        
        llm_chain = get_rtl_writer(llm) # Renamed to avoid conflict with `llm` import

        self.generated_tb = testbench
        self.generated_if = interface

        # Prepare the input dictionary for the LLM chain
        chain_inputs = {
            "input_spec": input_spec,
            "examples_prompt": RTL_4_SHOT_EXAMPLES,
            "module_interface": self.generated_if,
            "testbench": self.generated_tb,
            "failure_entry": failure_entry
        }

        # Limit the length of the previews for readability in logs
        input_spec_display = (input_spec[:50] + '...') if len(input_spec) > 50 else input_spec
        module_interface_display = (self.generated_if[:50] + '...') if len(self.generated_if) > 50 else self.generated_if
        testbench_display = (self.generated_tb[:50] + '...') if len(self.generated_tb) > 50 else self.generated_tb

        logger.debug(f"Invoking LLM with chain inputs: "
                    f"input_spec='{input_spec_display}', "
                    f"module_interface='{module_interface_display}', "
                    f"testbench='{testbench_display}'")

        response: RTLOutputFormat = llm_chain.invoke(chain_inputs)

        # Log the LLM's response for debugging and transparency
        logger.info("LLM Response received.")
        logger.info(f"Reasoning:\n{response.reasoning}")
        logger.info(f"Module (first 200 chars):\n{response.module[:200]}...")

        rtl_code = response.module

        logger.info("Initial rtl:")
        logger.info(rtl_code)

        return rtl_code


