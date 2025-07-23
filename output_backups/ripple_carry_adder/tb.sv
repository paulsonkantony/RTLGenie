module ripple_carry_adder_4bit_tb();
    // Signal declarations
    logic [3:0] A;
    logic [3:0] B;
    logic Cin;
    logic [3:0] S;
    logic Cout;
    logic [3:0] expected_S;
    logic expected_Cout;
    int mismatch_count;

    // Instantiate the Device Under Test (DUT)
    ripple_carry_adder_4bit dut(
        .A(A),
        .B(B),
        .Cin(Cin),
        .S(S),
        .Cout(Cout)
    );

    // Initialize signals
    initial begin
        mismatch_count = 0;
        // Test case 1: A = 0, B = 0, Cin = 0
        A = 4'd0; B = 4'd0; Cin = 1'b0; expected_S = 4'd0; expected_Cout = 1'b0;
        #10;
        check_output();

        // Test case 2: A = 1, B = 1, Cin = 0 (S = 2, Cout = 0)
        A = 4'd1; B = 4'd1; Cin = 1'b0; expected_S = 4'd2; expected_Cout = 1'b0;
        #10;
        check_output();

        // Test case 3: A = 15, B = 1, Cin = 0 (S = 0, Cout = 1) - testing overflow
        A = 4'd15; B = 4'd1; Cin = 1'b0; expected_S = 4'd0; expected_Cout = 1'b1;
        #10;
        check_output();

        // Finish simulation
        if (mismatch_count == 0)
            $display("SIMULATION PASSED");
        else
            $display("SIMULATION FAILED - %0d mismatches detected", mismatch_count);
        $finish;
    end

    // Task to check output and log mismatches
    task check_output();
        if (S !== expected_S || Cout !== expected_Cout) begin
            $display("Mismatch detected at time %0t", $time);
            $display("Input A = %b, B = %b, Cin = %b", A, B, Cin);
            $display("Expected Output S = %b, Cout = %b", expected_S, expected_Cout);
            $display("Actual Output S = %b, Cout = %b", S, Cout);
            mismatch_count++;
        end
    endtask
endmodule