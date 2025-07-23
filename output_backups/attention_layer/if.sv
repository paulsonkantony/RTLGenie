module attention_qkt(
    input  logic clk,
    input  logic reset_n,
    input  logic [511:0] I,    // 4x16 Input Embedding as 512 bits
    input  logic [255:0] WQ,   // 16x16 Query Weight as 256 bits
    input  logic [255:0] WK,    // 16x16 Key Weight as 256 bits
    output logic [511:0] Q,    // 4x16 Query Matrix as 512 bits
    output logic [511:0] K,    // 4x16 Key Matrix as 512 bits
    output logic [15:0] S      // 4x4 Score Matrix as 16 bits
);
