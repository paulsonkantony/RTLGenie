module AXI4LiteSlave #(parameter NUM_REGISTERS = 4, parameter BASE_ADDRESS = 32'h80000000)(
    input  logic                  clk,
    input  logic                  reset,
    input  logic [31:0]          AWADDR,
    input  logic                  AWVALID,
    output logic                  AWREADY,
    input  logic [31:0]          WDATA,
    input  logic                  WVALID,
    output logic                  WREADY,
    output logic [1:0]           BRESP,
    output logic                  BVALID,
    input  logic                  BREADY,
    input  logic [31:0]          ARADDR,
    input  logic                  ARVALID,
    output logic                  ARREADY,
    output logic [31:0]          RDATA,
    output logic [1:0]           RRESP,
    output logic                  RVALID,
    input  logic                  RREADY
);

    // Internal signals
    logic [31:0] reg_file [0:NUM_REGISTERS-1];
    logic [1:0] state, next_state;
    localparam IDLE = 2'b00, WRITE = 2'b01, READ = 2'b10;
    logic valid_addr;
    logic [31:0] reg_index;

    // Reset logic for initializing registers
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            for (int i = 0; i < NUM_REGISTERS; i++) begin
                reg_file[i] <= 32'b0;
            end
            state <= IDLE;
        end
    end

    // State Machine for AXI control
    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
        end else begin
            state <= next_state;
        end
    end

    // Address logic to calculate index
    always_comb begin
        valid_addr = 1'b0;
        if (AWADDR >= BASE_ADDRESS && (AWADDR - BASE_ADDRESS) % 4 == 0) begin
            reg_index = (AWADDR - BASE_ADDRESS) >> 2; // Calculate register index
            if (reg_index < NUM_REGISTERS) begin
                valid_addr = 1'b1;
            end
        end
    end

    // Combinational Logic for next state and output
    always_comb begin
        next_state = state;
        AWREADY = 0;
        WREADY = 0;
        ARREADY = 0;
        RVALID = 0;
        BVALID = 0;
        BRESP = 2'b00; // OKAY by default
        RRESP = 2'b00; // OKAY by default

        case (state)
            IDLE: begin
                if (AWVALID) begin
                    AWREADY = 1;
                    if (WVALID) begin
                        WREADY = 1;
                        next_state = WRITE;
                    end
                end else if (ARVALID) begin
                    ARREADY = 1;
                    next_state = READ;
                end
            end
            WRITE: begin
                if (valid_addr) begin
                    reg_file[reg_index] = WDATA;
                    BVALID = 1;
                    next_state = IDLE;
                end else begin
                    BRESP = 2'b10; // SLVERR for invalid address
                    next_state = IDLE;
                end
            end
            READ: begin
                if (valid_addr) begin
                    RDATA = reg_file[reg_index];
                    RVALID = 1;
                    next_state = IDLE;
                end else begin
                    RRESP = 2'b10; // SLVERR for invalid address
                    next_state = IDLE;
                end
            end
        endcase
    end

endmodule // AXI4LiteSlave