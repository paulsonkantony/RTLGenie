module attention_qkt(
    input  logic clk,
    input  logic reset_n,
    input  logic [511:0] I,    // 4x16 Input Embedding as 512 bits
    input  logic [255:0] WQ,   // 16x16 Query Weight as 256 bits
    input  logic [255:0] WK,   // 16x16 Key Weight as 256 bits
    output logic [511:0] Q,    // 4x16 Query Matrix as 512 bits
    output logic [511:0] K,    // 4x16 Key Matrix as 512 bits
    output logic [15:0] S      // 4x4 Score Matrix as 16 bits
);

    // Internal signals for Q and K calculations
    logic [511:0] Q_int, K_int;
    logic [15:0] S_int;
    logic [3:0] i; // Iteration counter for matrix multiplication

    // Sequential logic for output registers
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            Q <= 0;
            K <= 0;
            S <= 0;
        end else begin
            Q <= Q_int;
            K <= K_int;
            S <= S_int;
        end
    end

    // Combinational logic for Q and K computation
    always @(*) begin
        // Initializing outputs
        Q_int = 0;
        K_int = 0;
        // Calculate Q and K based on input and weights
        for (i = 0; i < 4; i++) begin
            Q_int[i*128 +: 128] = I[i*128 +: 128] * WQ;
            K_int[i*128 +: 128] = I[i*128 +: 128] * WK;
        end
        // Calculate the Score S
        S_int = 0; // Initialize
        for (i = 0; i < 4; i++) begin
            S_int = S_int + (Q_int[i*128 +: 128] * K_int[i*128 +: 128] ); // Logical transpose held
        end
    end

endmodule