module AsyncFIFO(
    input  logic CLK_WR,
    input  logic CLK_RD,
    input  logic reset,
    input  logic [31:0] din,
    input  logic wr_en,
    output logic wr_rdy,
    output logic full,
    output logic rd_rdy,
    output logic empty,
    output logic [31:0] dout,
    input  logic rd_en
);
