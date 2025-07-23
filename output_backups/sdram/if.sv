module SDRAM_Module(
    input  logic clk,
    input  logic cs_n,
    input  logic ras_n,
    input  logic cas_n,
    input  logic we_n,
    input  logic [7:0] addr,
    inout  logic [7:0] dq
);