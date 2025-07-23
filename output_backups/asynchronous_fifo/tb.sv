module AsyncFIFO_tb();
    // Signal declarations
    logic CLK_WR;
    logic CLK_RD;
    logic reset;
    logic [31:0] din;
    logic wr_en;
    logic wr_rdy;
    logic full;
    logic rd_rdy;
    logic empty;
    logic [31:0] dout;
    logic rd_en;
    logic [31:0] expected_dout;
    int mismatch_count;
    reg [31:0] input_queue [$];
    reg [31:0] output_queue [$];
    reg [31:0] expected_queue [$];
    localparam MAX_QUEUE_SIZE = 10;

    // Instantiate the DUT
    AsyncFIFO dut(
        .CLK_WR(CLK_WR),
        .CLK_RD(CLK_RD),
        .reset(reset),
        .din(din),
        .wr_en(wr_en),
        .wr_rdy(wr_rdy),
        .full(full),
        .rd_rdy(rd_rdy),
        .empty(empty),
        .dout(dout),
        .rd_en(rd_en)
    );

    // Clock generation
    initial begin
        CLK_WR = 0;
        forever #5 CLK_WR = ~CLK_WR;
    end

    initial begin
        CLK_RD = 0;
        forever #7 CLK_RD = ~CLK_RD;
    end

    // Test stimulus
    initial begin
        // Initialize signals
        reset = 1;
        din = 0;
        wr_en = 0;
        rd_en = 0;
        mismatch_count = 0;
        expected_dout = 0;

        // Wait for 2 clock cycles in reset
        @(posedge CLK_WR);
        @(posedge CLK_WR);
        reset = 0;

        // Test writing to FIFO
        for (int i = 0; i < 10; i++) begin
            din = i;
            wr_en = 1;
            @(posedge CLK_WR);
            if (wr_rdy) begin
                expected_queue.push_back(din);
            end
            wr_en = 0;
            @(negedge CLK_WR);
        end

        // Handle reading from FIFO
        rd_en = 1;
        for (int j = 0; j < 10; j++) begin
            @(posedge CLK_RD);
            if (rd_rdy) begin
                expected_dout = expected_queue[0];
                output_queue.push_back(dout);
                expected_queue.delete(0);
            end
        end

        // End simulation
        #20;
        if (mismatch_count == 0) 
            $display("SIMULATION PASSED");
        else
            $display("SIMULATION FAILED - %0d mismatches detected", mismatch_count);
        $finish;
    end

    always @(posedge CLK_RD) begin
        // Check for mismatches
        if (output_queue.size() > 0 && dout !== expected_dout) begin
            $display("Mismatch at time %0t: expected output=%b, actual output=%b", $time, expected_dout, dout);
            mismatch_count++;  
            // Display last mismatch queue
            for (int i = 0; i < output_queue.size(); i++) begin
                $display("Cycle %d: Expected=%b, Actual=%b", i, expected_queue[i], output_queue[i]);
            end
        end
    end

endmodule
