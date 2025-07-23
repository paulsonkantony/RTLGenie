module AXI4LiteSlave_tb();
    
    parameter NUM_REGISTERS = 4;
    parameter BASE_ADDRESS = 32'h80000000;
    parameter CLK_PERIOD = 10;
    
    // Signal declarations
    logic                  clk;
    logic                  reset;
    logic [31:0]          AWADDR;
    logic                  AWVALID;
    logic                  AWREADY;
    logic [31:0]          WDATA;
    logic                  WVALID;
    logic                  WREADY;
    logic [1:0]           BRESP;
    logic                  BVALID;
    logic                  BREADY;
    logic [31:0]          ARADDR;
    logic                  ARVALID;
    logic                  ARREADY;
    logic [31:0]          RDATA;
    logic [1:0]           RRESP;
    logic                  RVALID;
    logic                  RREADY;
    
    // Mismatch counter
    int mismatch_count; 
    reg [31:0] expected_data;
    
    // Instantiate the DUT
    AXI4LiteSlave #(
        .NUM_REGISTERS(NUM_REGISTERS),
        .BASE_ADDRESS(BASE_ADDRESS)
    ) dut (
        .clk(clk),
        .reset(reset),
        .AWADDR(AWADDR),
        .AWVALID(AWVALID),
        .AWREADY(AWREADY),
        .WDATA(WDATA),
        .WVALID(WVALID),
        .WREADY(WREADY),
        .BRESP(BRESP),
        .BVALID(BVALID),
        .BREADY(BREADY),
        .ARADDR(ARADDR),
        .ARVALID(ARVALID),
        .ARREADY(ARREADY),
        .RDATA(RDATA),
        .RRESP(RRESP),
        .RVALID(RVALID),
        .RREADY(RREADY)
    );
    
    // Clock generation
    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end
    
    // Test stimulus
    initial begin
        // Initialize signals
        reset = 1;
        mismatch_count = 0;
        AWADDR = 0;
        AWVALID = 0;
        WDATA = 0;
        WVALID = 0;
        BREADY = 0;
        ARADDR = 0;
        ARVALID = 0;
        RREADY = 0;
        
        // Wait for 2 clock cycles and release reset
        @(posedge clk);
        @(posedge clk);
        reset = 0;
        
        // Test case 1: Write to register
        AWADDR = BASE_ADDRESS;
        WDATA = 32'h12345678;
        AWVALID = 1;
        WVALID = 1;
        
        @(posedge clk);
        AWVALID = 0;  // Clear AWVALID after one cycle
        WVALID = 0;   // Clear WVALID after one cycle
        BREADY = 1;   // Ready for response
        
        @(posedge clk);
        if (BVALID && (BRESP == 2'b00)) begin
            $display("Write transaction successful.");
        end else begin
            mismatch_count++;
        end
        
        // Test case 2: Read from register
        ARADDR = BASE_ADDRESS;
        ARVALID = 1;
        RREADY = 1;
        
        @(posedge clk);
        ARVALID = 0;  // Clear ARVALID after one cycle
        RREADY = 0;   // Clear RREADY after one cycle
        
        expected_data = 32'h12345678;
        
        @(posedge clk);
        if (RVALID) begin
            if (RDATA !== expected_data) begin
                $display("Mismatch detected: expected %h, got %h", expected_data, RDATA);
                mismatch_count++;
            end
        end
        
        // Finalize simulation
        if (mismatch_count == 0) begin
            $display("SIMULATION PASSED");
        end else begin
            $display("SIMULATION FAILED - %0d mismatches detected", mismatch_count);
        end
        $finish;
    end

endmodule
