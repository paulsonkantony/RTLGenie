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

    // Parameters
    localparam DEPTH = 8;
    localparam ADDR_WIDTH = 3; // 2^3 = 8 depth

    // Memory implementation
    logic [31:0] fifo_mem[DEPTH-1:0];
    logic [ADDR_WIDTH-1:0] wr_ptr, rd_ptr; // Read and write pointers
    logic [ADDR_WIDTH-1:0] wr_ptr_sync, rd_ptr_sync; // Synchronised pointers

    // Full and Empty Flags
    assign full = (wr_ptr_sync[ADDR_WIDTH-1:0] + 1) == rd_ptr_sync;  // Adjusted condition for full
    assign empty = (wr_ptr_sync == rd_ptr_sync);

    // Read/write ready signals
    assign wr_rdy = ~full;
    assign rd_rdy = ~empty;

    // Pointer Management
    always_ff @(posedge CLK_WR or posedge reset) begin
        if (reset) begin
            wr_ptr <= 0;
        end else if (wr_en && wr_rdy) begin
            fifo_mem[wr_ptr] <= din;
            wr_ptr <= (wr_ptr + 1) % DEPTH; // wrap around logic
        end
    end

    always_ff @(posedge CLK_RD or posedge reset) begin
        if (reset) begin
            rd_ptr <= 0;
            dout <= 0; // Default to zero on reset
        end else if (rd_en && rd_rdy) begin
            dout <= fifo_mem[rd_ptr];
            rd_ptr <= (rd_ptr + 1) % DEPTH; // wrap around logic
        end
    end

    // CDC Synchronization for write pointer into read domain
    always_ff @(posedge CLK_RD or posedge reset) begin
        if (reset) begin
            wr_ptr_sync <= 0;
        end else begin
            wr_ptr_sync <= wr_ptr; // single flop synchronization
        end
    end

    // CDC Synchronization for read pointer into write domain
    always_ff @(posedge CLK_WR or posedge reset) begin
        if (reset) begin
            rd_ptr_sync <= 0;
        end else begin
            rd_ptr_sync <= rd_ptr; // single flop synchronization
        end
    end

endmodule
