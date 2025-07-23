import logging
from typing import Dict, List, Tuple

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser # Not used in optimized get_tb_writer

# Assuming these are defined elsewhere and correctly imported
from prompts import TB_4_SHOT_EXAMPLES 
from llm import llm # Ensure llm is an initialized LangChain LLM object

import logger_config
logger = logging.getLogger("root")
logger.info("Imported TB Generator module")

# --- Constants for Prompts  ---

DISPLAY_MOMENT_PROMPT = """
1. When the first mismatch occurs, display the input signals, output signals and expected output signals at that time.
2. For multiple-bit signals displayed in HEX format, also display the BINARY format if its width <= 64.
"""

DISPLAY_QUEUE_PROMPT = """
1. If module to test is sequential logic (like including an FSM):
    1.1. Store input signals, output signals, expected output signals and reset signals in a queue with MAX_QUEUE_SIZE;
        When the first mismatch occurs, display the queue content after storing it. Make sure the mismatched signal can be displayed.
    1.2. MAX_QUEUE_SIZE should be set according to the requirement of the module.
        For example, if the module has a 3-bit state, MAX_QUEUE_SIZE should be at least 2 ** 3 = 8.
        And if the module was to detect a pattern of 8 bits, MAX_QUEUE_SIZE should be at least (8 + 1) = 9.
        However, to control log size, NEVER set MAX_QUEUE_SIZE > 10.
    1.3. The clocking of queue and display should be same with the clocking of tb_match detection.
        For example, if 'always @(posedge clk, negedge clk)' is used to detect mismatch,
        It should also be used to push queue and display first error.
2. If module to test is combinational logic:
    When the first mismatch occurs, display the input signals, output signals and expected output signals at that time.
3. For multiple-bit signals displayed in HEX format, also display the BINARY format if its width <= 64.

<display_queue_example>
// Queue-based simulation mismatch display

reg [INPUT_WIDTH-1:0] input_queue [$];
reg [OUTPUT_WIDTH-1:0] got_output_queue [$];
reg [OUTPUT_WIDTH-1:0] golden_queue [$];
reg reset_queue [$];

localparam MAX_QUEUE_SIZE = 5;

always @(posedge clk, negedge clk) begin
    if (input_queue.size() >= MAX_QUEUE_SIZE - 1) begin
        input_queue.delete(0);
        got_output_queue.delete(0);
        golden_queue.delete(0);
        reset_queue.delete(0);
    end

    input_queue.push_back(input_data);
    got_output_queue.push_back(got_output);
    golden_queue.push_back(golden_output);
    reset_queue.push_back(rst);

    // Check for first mismatch
    if (got_output !== golden_output) begin
        $display("Mismatch detected at time %t", $time);
        $display("\nLast %d cycles of simulation:", input_queue.size());


        for (int i = 0; i < input_queue.size(); i++) begin
            if (got_output_queue[i] === golden_queue[i]) begin
                $display("Got Match at");
            end else begin
                $display("Got Mismatch at");
            end
            $display("Cycle %d, reset %b, input %h, got output %h, exp output %h",
                i,
                reset_queue[i],
                input_queue[i],
                got_output_queue[i],
                golden_queue[i]
            );
        end
    end

end
</display_queue_example>
"""

# --- Pydantic Model ---

class TBOutputFormat(BaseModel):
    """
    Defines the structured output format for the testbench generation.
    """
    reasoning: str = Field(
        description="All reasoning steps and advices to avoid syntax error"
    )
    interface: str = Field(
        description="The IO part of a SystemVerilog module, NOT containing the module implementation. "
                    "This is just to show what the inputs and outputs of the DUT are"
    )
    testbench: str = Field(
        description="The testbench module code to test the module. "
                    "This should be error-free and ready for output to .SV file that can be run using a verilog simulator"
    )

# --- TB Writer Function ---

def get_tb_writer(llm):
    """
    Creates a LangChain chain for generating SystemVerilog testbenches.

    Args:
        llm: The Language Model instance (e.g., ChatOpenAI).

    Returns:
        A LangChain Runnable that takes 'input_spec', 'examples_prompt',
        'display_prompt' as input and returns a TBOutputFormat object.
    """

    structured_tb_writer = llm.with_structured_output(TBOutputFormat)

    system_prompt = """
You are an expert in SystemVerilog design.
You can always write SystemVerilog code with no syntax errors and always reach correct functionality.
"""

    messages = [
        ("system", system_prompt),
        ("human", """
In order to test a module generated with the given natural language specification, please follow these steps:

### Step 1: Write the IO Interface
- Create an IO interface for the module.
- Ensure the module name and port names/types match the input specification exactly.

**Example:**
```systemverilog
module TopModule(
    input  logic clk,
    input  logic reset,
    input  logic in_,
    output logic out
);
```
            
### Step 2: Write the Testbench
- Create a testbench to test the module.

**Example:**
Example:
    ```systemverilog
    module TopModule_tb();
        // Signal declarations
        logic clk;
        logic reset;
        logic in_;
        logic out;
        logic expected_out;
        int mismatch_count;

        // Instantiate the DUT
        TopModule dut(
            .clk(clk),
            .reset(reset),
            .in_(in_),
            .out(out)
        );

        // Clock generation
        initial begin
            clk = 0;
            forever #5 clk = ~clk;
        end

        // Test stimulus and checking
        initial begin
            // Initialize signals
            reset = 1;
            in_ = 0;
            mismatch_count = 0;
            expected_out = 0;

            // Wait for 2 clock cycles and release reset
            @(posedge clk);
            @(posedge clk);
            reset = 0;

            // Test case 1: No consecutive ones
            @(posedge clk); in_ = 0; expected_out = 0;
            @(posedge clk); in_ = 1; expected_out = 0;
            @(posedge clk); in_ = 0; expected_out = 0;
            @(posedge clk); in_ = 1; expected_out = 0;

            // Test case 2: Two consecutive ones
            @(posedge clk); in_ = 1; expected_out = 0;
            @(posedge clk); in_ = 1; expected_out = 0;
            @(posedge clk); in_ = 0; expected_out = 1;
            @(posedge clk); in_ = 0; expected_out = 0;

            // Test case 3: Three consecutive ones
            @(posedge clk); in_ = 1; expected_out = 0;
            @(posedge clk); in_ = 1; expected_out = 0;
            @(posedge clk); in_ = 1; expected_out = 1;
            @(posedge clk); in_ = 0; expected_out = 1;

            // Test case 4: Reset during operation
            @(posedge clk); in_ = 1; expected_out = 0;
            @(posedge clk); in_ = 1; expected_out = 0;
            @(posedge clk); reset = 1; in_ = 0; expected_out = 0;
            @(posedge clk); reset = 0; in_ = 0; expected_out = 0;

            // End simulation
            #20 $finish;
        end

        // Monitor changes and check outputs
        always @(negedge clk) begin
            if (out !== expected_out) begin
                $display("Mismatch at time %0t: input=%b, actual_output=%b, expected_output=%b",
                        $time, in_, out, expected_out);
                mismatch_count++;
            end else begin
                $display("Match at time %0t: input=%b, output=%b",
                        $time, in_, out);
            end
        end

        // Final check and display results
        final begin
            if (mismatch_count == 0)
                $display("SIMULATION PASSED");
            else
                $display("SIMULATION FAILED - %0d mismatches detected", mismatch_count);
        end

    endmodule
    ```

The module interface should EXACTLY MATCH the description in input_spec.
(Including the module name, input/output ports names, and their types)

<input_spec>
{input_spec}
</input_spec>

The testbench should:
1. Instantiate the module according to the IO interface;
2. Generate input stimulate signals and expected output signals according to input_spec;
3. Apply the input signals to the module, count the number of mismatches between the output signals with the expected output signals;
4. Every time when a check occurs, no matter match or mismatch, display input signals, output signals and expected output signals;
5. When simulation ends, ADD DISPLAY "SIMULATION PASSED" if no mismatch occurs, otherwise display:
    "SIMULATION FAILED - x MISMATCHES DETECTED, FIRST AT TIME y".
6. To avoid ambiguity, please use the reverse edge to do output check. (If RTL runs at posedge, use negedge to check the output)
7. For pure combinational module (especially those without clk),
    the expected output should be checked at the exact moment when the input is changed;
8. Avoid using keyword "continue"
9. Take extra care not to introduce infinite loops in the testbench!

-----------------------------------------

{failure_entry} 
         
-----------------------------------------

{examples_prompt}
         
-----------------------------------------

Please also follow the display prompt below:
{display_prompt}
         
For pattern detector, if no specification is found in input_spec,
suppose the "detected" output will be asserted on the cycle AFTER the pattern appears in input.
Like when detecting pattern "11", should be like:
// Test case : Two consecutive ones
@(posedge clk); in_ = 1; expected_out = 0;
@(posedge clk); in_ = 1; expected_out = 0;
@(posedge clk); in_ = 0; expected_out = 1;

"""
        ),
    ]

    tb_gen_prompt = ChatPromptTemplate.from_messages(messages)

    return  tb_gen_prompt | structured_tb_writer


class TBGenerator:
    """
    Generates SystemVerilog testbenches using an LLM,
    with capabilities for iterative refinement based on failed simulations.
    """
    def __init__(self):
        """
        Initializes the TBGenerator.
        """
        self.gen_display_queue: bool = True
        logger.info("TBGenerator initialized.")


    def chat(self, input_spec: str, failure_entry = "") -> Tuple[str, str]:
        """
        Invokes the LLM to generate a testbench and interface based on the input specification

        Args:
            input_spec (str): The natural language specification for the module to be tested.

        Returns:
            Tuple[str, str]: A tuple containing the generated testbench code and
                             the generated module interface code.
        """
        
        llm_chain = get_tb_writer(llm) # Renamed to avoid conflict with `llm` import

        # Determine which display prompt to use based on the flag
        display_prompt_to_use = DISPLAY_QUEUE_PROMPT if self.gen_display_queue else DISPLAY_MOMENT_PROMPT

        # Prepare the input dictionary for the LLM chain
        chain_inputs = {
            "input_spec": input_spec,
            "examples_prompt": TB_4_SHOT_EXAMPLES,
            "display_prompt": display_prompt_to_use,
            "failure_entry" : failure_entry
        }

        logger.debug(f"Invoking LLM with input_spec: '{input_spec[:50]}...' and display type: {'Queue' if self.gen_display_queue else 'Moment'}")
        response: TBOutputFormat = llm_chain.invoke(chain_inputs)

        # Log the LLM's response for debugging and transparency
        logger.info("LLM Response received.")
        logger.info(f"Reasoning:\n{response.reasoning}")
        logger.info(f"Interface:\n{response.interface}")
        logger.info(f"Testbench (first 200 chars):\n{response.testbench[:200]}...")

        logger.info("Specification:")
        logger.info(input_spec)
        logger.info("Initial tb:")
        logger.info(response.testbench)
        logger.info("Initial if:")
        logger.info(response.interface)
            
        return (response.testbench, response.interface)
    

# obj = TBGenerator() 


# obj.chat(input_spec)

