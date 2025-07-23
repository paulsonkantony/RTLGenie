module attention_qkt_tb();
    // Signal declarations
    logic clk;
    logic reset_n;
    logic [511:0] I;
    logic [255:0] WQ;
    logic [255:0] WK;
    logic [511:0] Q;
    logic [511:0] K;
    logic [15:0] S;
    logic [511:0] expected_Q;
    logic [511:0] expected_K;
    logic [15:0] expected_S;
    int mismatch_count;

    // Instantiate the DUT
    attention_qkt dut(
        .clk(clk),
        .reset_n(reset_n),
        .I(I),
        .WQ(WQ),
        .WK(WK),
        .Q(Q),
        .K(K),
        .S(S)
    );

    // Clock generation
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Test stimulus and checking
    initial begin
        // Initialize signals
        reset_n = 1;
        I = 0;
        WQ = 0;
        WK = 0;
        mismatch_count = 0;

        // Wait for 2 clock cycles and release reset
        @(posedge clk);
        @(posedge clk);
        reset_n = 0;

        // Example Test case: Set the weights and input embedding
        I = 'h0000000000000000000000000000000000000000000000000000000000000000;
        WQ = 'h00000000000000000000000000000000;
        WK = 'h00000000000000000000000000000000;

        // Wait for a clock cycle after setting inputs
        @(posedge clk);
        // Here, expected outputs calculations will depend on the module implementation
        expected_Q = I * WQ; // Placeholder calculation
        expected_K = I * WK; // Placeholder calculation
        expected_S = expected_Q * expected_K; // Placeholder calculation with transpositions assumed
        @(negedge clk);
        check_output(); // Output checking procedure

        // Final simulation check
        #20 if(mismatch_count == 0)
            $display("SIMULATION PASSED");
        else
            $display("SIMULATION FAILED - %0d mismatches detected", mismatch_count);
        $finish;
    end

    // Task to compare outputs
    task check_output();
        if (Q !== expected_Q || K !== expected_K || S !== expected_S) begin
            $display("Mismatch detected at time %0t:", $time);
            $display("  Expected Q: %h, Got Q: %h", expected_Q, Q);
            $display("  Expected K: %h, Got K: %h", expected_K, K);
            $display("  Expected S: %h, Got S: %h", expected_S, S);
            mismatch_count++;
        end else begin
            $display("Outputs match at time %0t:", $time);
        end
    endtask

endmodule