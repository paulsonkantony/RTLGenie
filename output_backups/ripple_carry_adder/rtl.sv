module ripple_carry_adder_4bit(
    input  logic [3:0] A,
    input  logic [3:0] B,
    input  logic Cin,
    output logic [3:0] S,
    output logic Cout
);

    // Intermediate carries between the full adders
    logic [3:1] carry_intermediate;

    // Instantiate the 1-bit full adders
    full_adder_1bit fa0 ( .A(A[0]), .B(B[0]), .Cin(Cin), .S(S[0]), .Cout(carry_intermediate[1]) );
    full_adder_1bit fa1 ( .A(A[1]), .B(B[1]), .Cin(carry_intermediate[1]), .S(S[1]), .Cout(carry_intermediate[2]) );
    full_adder_1bit fa2 ( .A(A[2]), .B(B[2]), .Cin(carry_intermediate[2]), .S(S[2]), .Cout(carry_intermediate[3]) );
    full_adder_1bit fa3 ( .A(A[3]), .B(B[3]), .Cin(carry_intermediate[3]), .S(S[3]), .Cout(Cout) );

endmodule

module full_adder_1bit(
    input  logic A,
    input  logic B,
    input  logic Cin,
    output logic S,
    output logic Cout
);
    // Full adder logic
    assign S = A ^ B ^ Cin; // Sum calculation
    assign Cout = (A & B) | (Cin & (A ^ B)); // Carry-out calculation
endmodule