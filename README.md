# ⚙️ RTLGenie: AI-Powered SystemVerilog Design & Verification

**RTLGenie** is an advanced framework that automates the generation and verification of SystemVerilog RTL (Register-Transfer Level) designs and their corresponding testbenches. Based on the **MAGE (Multi-Agent Engine)** methodology, RTLGenie significantly enhances the hardware design workflow by providing an intelligent, iterative system for design creation and debugging.

---

## 🧩 Architecture and Core Components

<img width="2452" height="1322" alt="Tool_HLD" src="https://github.com/user-attachments/assets/2075c66a-e742-4e64-bbd7-4cce7e2e188b" />

RTLGenie operates through a cohesive architecture of interconnected Python modules, each contributing a specialized function to the overall design and verification pipeline:

### 🛠️ RTL Generation (`rtl_generator.py`)

This module is responsible for synthesizing SystemVerilog RTL code from natural language specifications. It leverages a Large Language Model (LLM) to translate high-level design requirements into synthesizable hardware descriptions. The LLM is guided by a comprehensive prompt that incorporates design principles, syntax rules, and relevant examples, and it can dynamically refine its output based on feedback from simulation failures. The generated output is structured as `RTLOutputFormat`, providing the module code and design rationale.

### 🧪 Testbench Generation (`tb_generator.py`)

This component focuses on creating robust SystemVerilog testbenches essential for verifying RTL module functionality. An LLM is employed to develop testbenches that include sophisticated input stimulus generation, accurate expected output calculation, and effective mismatch detection logic. It supports flexible error display mechanisms, such as "moment-based" and "queue-based" reporting for sequential designs. The output is formatted as `TBOutputFormat`, encompassing the testbench code, module interface, and the generation's underlying reasoning.

### 🕵️ Simulation Judgment (`sim_judge.py`)

Acting as an intelligent diagnostic agent, this module analyzes failed simulations. It utilizes an LLM to meticulously review simulation logs, the initial design specification, and the problematic RTL and testbench code. Its primary function is to precisely determine whether the **RTL module** or the **testbench** is the root cause of functional mismatches or errors. It provides detailed reasoning and actionable suggestions for corrections. The output is presented in `JudgeFormat`, clearly indicating `rtl_needs_fix`, `tb_needs_fix`, and a comprehensive `reasoning` string.

### 🔁 Iterative Review and Refinement (`sim_reviewer.py`)

This module serves as the central orchestration unit for the entire iterative verification and correction workflow. It employs a **LangGraph StateGraph** to manage the design flow, incorporating various nodes for systematic checks:

* 🔍 **RTL Syntax Check**: Compiles the RTL using `iverilog` to identify syntax errors.
* 🧩 **Testbench Execution Check**: Compiles and executes both the testbench and RTL to ensure basic operational integrity.
* ⚡ **Functional Mismatch Check**: Analyzes simulation outputs for any functional deviations from the specification.
* 🔧 **Automated Correction**: Based on the `sim_judge`'s analysis, it dynamically invokes either the `RTLGenerator` or `TBGenerator` to apply necessary fixes.

This continuous loop of compilation, simulation, and refinement persists until the design successfully passes all verification steps or a predefined maximum iteration limit is reached.

---

## 🚀 Getting Started

### 📥 Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/paulsonkantony/RTLGenie.git
   cd RTLGenie
   ```

2. **Install Python dependencies**:

3. **Install `iverilog`**:

   * 🐧 **Ubuntu**: `sudo apt-get install iverilog`
   * 🍎 **macOS (Homebrew)**: `brew install iverilog`
   * 🪟 **Windows**: Download and install from the [Icarus Verilog website](https://www.google.com/search?q=http://iverilog.icarus.com/)

### 🧰 Usage

To initiate the generation and verification process with RTLGenie:

1. 📝 **Define your `input_spec` and `name`**:
   Prepare a comprehensive natural language specification detailing your desired SystemVerilog module, including its functionality, interface, and any structural or behavioral constraints. This should be placed in `config.toml`.

2. 🔐 **Define the API for the LLM**:
   AzureOpenAI instance has been used to prepare this proof-of-concept. Ollama instance can be configured by changing `llm.py`.

3. ▶️ **Run `top.py`**

---

## 📚 Citation

RTLGenie is developed based on the principles and foundational work of the **MAGE: A Multi-Agent Engine for Automated RTL Code Generation** project.

> Y. Zhao, H. Zhang, H. Huang, Z. Yu, and J. Zhao, ‘MAGE: A Multi-Agent Engine for Automated RTL Code Generation’, *arXiv \[cs.AR]*. 2024.

🔗 [Original MAGE Repository](https://github.com/stable-lab/MAGE)
