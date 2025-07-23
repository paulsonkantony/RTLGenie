module SDRAM_Module_tb();
    // Signal declarations
    logic clk;
    logic cs_n;
    logic ras_n;
    logic cas_n;
    logic we_n;
    logic [7:0] addr;
    logic [7:0] dq;
    logic [7:0] dq_out;
    logic [7:0] expected_out;
    int mismatch_count;

    localparam MAX_QUEUE_SIZE = 10; // Set based on the module complexity
    logic [7:0] input_queue [$];
    logic [7:0] got_output_queue [$];
    logic [7:0] golden_queue [$];
    logic [3:0] reset_queue [$]; // Update for deeper history

    // Instantiate the DUT
    SDRAM_Module dut (
        .clk(clk),
        .cs_n(cs_n),
        .ras_n(ras_n),
        .cas_n(cas_n),
        .we_n(we_n),
        .addr(addr),
        .dq(dq)
    );

    // Clock generation
    initial begin
        clk = 0;
        forever #10 clk = ~clk; // 50 MHz clock
    end

    // Initialize signals and mismatch counter
    initial begin
        reset();
        mismatch_count = 0;

        // Test Write Operation
        test_write_operation();

        // Test Read Operation
        test_read_operation();

        // Test Refresh Operation
        test_refresh_operation();

        // End simulation
        #20;
        if (mismatch_count == 0) begin
            $display("SIMULATION PASSED");
        end else begin
            $display("SIMULATION FAILED - %0d mismatches detected", mismatch_count);
        end
        $finish;
    end

    // Reset procedure
    task reset();
        cs_n = 1;
        ras_n = 1;
        cas_n = 1;
        we_n = 1;
        addr = 0;
    endtask

    // Write operation test
    task test_write_operation();
        addr = 8'h01;
        we_n = 0; // Enable write
        dq = 8'hA5; // Data to write
        @(posedge clk);
        we_n = 1;
        dq_out = dq;  // Expected output should reflect the write value, observe during next clock
    endtask

    // Read operation test
    task test_read_operation();
        addr = 8'h01;
        cas_n = 0; // Assert CAS for read
        @(posedge clk);
        @(posedge clk);
        expected_out = dq_out;
        check_output();
        cas_n = 1; // Deassert CAS
    endtask

    // Refresh operation test
    task test_refresh_operation();
        ras_n = 0; // Assert RAS for refresh
        @(posedge clk);
        ras_n = 1; // Deassert RAS
    endtask

    // Check output and log mismatches
    task check_output();
        if (dq !== expected_out) begin
            $display("Mismatch detected at time %0t:", $time);
            $display("Input = %h, Expected Output = %h, Got Output = %h", addr, expected_out, dq);
            mismatch_count++;

            // Queue management
            if (input_queue.size() >= MAX_QUEUE_SIZE) begin
                input_queue.delete(0);
                got_output_queue.delete(0);
                golden_queue.delete(0);
                reset_queue.delete(0);
            end
            input_queue.push_back(addr);
            got_output_queue.push_back(dq);
            golden_queue.push_back(expected_out);
            reset_queue.push_back({cs_n, ras_n, cas_n, we_n});

            $display("Mismatch queue logged:");
            for (int i = 0; i < input_queue.size(); i++) begin
                $display("Cycle %d, Reset: %b, Input: %h, Got Output: %h, Expected Output: %h", i, reset_queue[i], input_queue[i], got_output_queue[i], golden_queue[i]);
            end

        end else begin
            $display("Match detected at time %0t:", $time);
            $display("Input = %h, Output = %h", addr, dq);
        end
    endtask

endmodule