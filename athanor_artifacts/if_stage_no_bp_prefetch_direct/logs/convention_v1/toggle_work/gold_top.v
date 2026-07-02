module gold_top (
	clk_i,
	rst_ni,
	boot_addr_i,
	req_i,
	instr_req_o,
	instr_addr_o,
	instr_gnt_i,
	instr_rvalid_i,
	instr_rdata_i,
	instr_bus_err_i,
	instr_intg_err_o,
	ic_tag_req_o,
	ic_tag_write_o,
	ic_tag_addr_o,
	ic_tag_wdata_o,
	ic_tag_rdata_i,
	ic_data_req_o,
	ic_data_write_o,
	ic_data_addr_o,
	ic_data_wdata_o,
	ic_data_rdata_i,
	ic_scr_key_valid_i,
	ic_scr_key_req_o,
	instr_valid_id_o,
	instr_new_id_o,
	instr_rdata_id_o,
	instr_rdata_alu_id_o,
	instr_rdata_c_id_o,
	instr_is_compressed_id_o,
	instr_gets_expanded_id_o,
	instr_expanded_id_o,
	instr_bp_taken_o,
	instr_fetch_err_o,
	instr_fetch_err_plus2_o,
	illegal_c_insn_id_o,
	dummy_instr_id_o,
	pc_if_o,
	pc_id_o,
	pmp_err_if_i,
	pmp_err_if_plus2_i,
	instr_valid_clear_i,
	pc_set_i,
	pc_mux_i,
	nt_branch_mispredict_i,
	nt_branch_addr_i,
	exc_pc_mux_i,
	exc_cause,
	dummy_instr_en_i,
	dummy_instr_mask_i,
	dummy_instr_seed_en_i,
	dummy_instr_seed_i,
	icache_enable_i,
	icache_inval_i,
	icache_ecc_error_o,
	branch_target_ex_i,
	csr_mepc_i,
	csr_depc_i,
	csr_mtvec_i,
	csr_mtvec_init_o,
	id_in_ready_i,
	pc_mismatch_alert_o,
	if_busy_o
);
	reg _sv2v_0;
	parameter [31:0] DmHaltAddr = 32'h1a110800;
	parameter [31:0] DmExceptionAddr = 32'h1a110808;
	parameter [0:0] DummyInstructions = 1'b0;
	parameter [0:0] ICache = 1'b0;
	parameter integer RV32ZC = 32'sd3;
	parameter [0:0] ICacheECC = 1'b0;
	parameter [0:0] ICacheTweakInfection = 1'b0;
	localparam [31:0] ibex_pkg_BUS_SIZE = 32;
	parameter [31:0] BusSizeECC = ibex_pkg_BUS_SIZE;
	localparam [31:0] ibex_pkg_ADDR_W = 32;
	localparam [31:0] ibex_pkg_IC_LINE_SIZE = 64;
	localparam [31:0] ibex_pkg_IC_LINE_BYTES = 8;
	localparam [31:0] ibex_pkg_IC_NUM_WAYS = 2;
	localparam [31:0] ibex_pkg_IC_SIZE_BYTES = 4096;
	localparam [31:0] ibex_pkg_IC_NUM_LINES = (ibex_pkg_IC_SIZE_BYTES / ibex_pkg_IC_NUM_WAYS) / ibex_pkg_IC_LINE_BYTES;
	localparam [31:0] ibex_pkg_IC_INDEX_W = $clog2(ibex_pkg_IC_NUM_LINES);
	localparam [31:0] ibex_pkg_IC_LINE_W = 3;
	localparam [31:0] ibex_pkg_IC_TAG_SIZE = ((ibex_pkg_ADDR_W - ibex_pkg_IC_INDEX_W) - ibex_pkg_IC_LINE_W) + 1;
	parameter [31:0] TagSizeECC = ibex_pkg_IC_TAG_SIZE;
	parameter [31:0] LineSizeECC = ibex_pkg_IC_LINE_SIZE;
	parameter [0:0] PCIncrCheck = 1'b0;
	parameter [0:0] ResetAll = 1'b0;
	localparam signed [31:0] ibex_pkg_LfsrWidth = 32;
	localparam [31:0] ibex_pkg_RndCnstLfsrSeedDefault = 32'hac533bf4;
	parameter [31:0] RndCnstLfsrSeed = ibex_pkg_RndCnstLfsrSeedDefault;
	localparam [159:0] ibex_pkg_RndCnstLfsrPermDefault = 160'h1e35ecba467fd1b12e958152c04fa43878a8daed;
	parameter [159:0] RndCnstLfsrPerm = ibex_pkg_RndCnstLfsrPermDefault;
	parameter [0:0] BranchPredictor = 1'b0;
	parameter [0:0] MemECC = 1'b0;
	parameter [31:0] MemDataWidth = (MemECC ? 39 : 32);
	input wire clk_i;
	input wire rst_ni;
	input wire [31:0] boot_addr_i;
	input wire req_i;
	output wire instr_req_o;
	output wire [31:0] instr_addr_o;
	input wire instr_gnt_i;
	input wire instr_rvalid_i;
	input wire [MemDataWidth - 1:0] instr_rdata_i;
	input wire instr_bus_err_i;
	output wire instr_intg_err_o;
	output wire [1:0] ic_tag_req_o;
	output wire ic_tag_write_o;
	output wire [ibex_pkg_IC_INDEX_W - 1:0] ic_tag_addr_o;
	output wire [TagSizeECC - 1:0] ic_tag_wdata_o;
	input wire [(ibex_pkg_IC_NUM_WAYS * TagSizeECC) - 1:0] ic_tag_rdata_i;
	output wire [1:0] ic_data_req_o;
	output wire ic_data_write_o;
	output wire [ibex_pkg_IC_INDEX_W - 1:0] ic_data_addr_o;
	output wire [LineSizeECC - 1:0] ic_data_wdata_o;
	input wire [(ibex_pkg_IC_NUM_WAYS * LineSizeECC) - 1:0] ic_data_rdata_i;
	input wire ic_scr_key_valid_i;
	output wire ic_scr_key_req_o;
	output wire instr_valid_id_o;
	output wire instr_new_id_o;
	output reg [31:0] instr_rdata_id_o;
	output reg [31:0] instr_rdata_alu_id_o;
	output reg [15:0] instr_rdata_c_id_o;
	output reg instr_is_compressed_id_o;
	output reg [1:0] instr_gets_expanded_id_o;
	output reg [15:0] instr_expanded_id_o;
	output wire instr_bp_taken_o;
	output reg instr_fetch_err_o;
	output reg instr_fetch_err_plus2_o;
	output reg illegal_c_insn_id_o;
	output reg dummy_instr_id_o;
	output wire [31:0] pc_if_o;
	output reg [31:0] pc_id_o;
	input wire pmp_err_if_i;
	input wire pmp_err_if_plus2_i;
	input wire instr_valid_clear_i;
	input wire pc_set_i;
	input wire [2:0] pc_mux_i;
	input wire nt_branch_mispredict_i;
	input wire [31:0] nt_branch_addr_i;
	input wire [1:0] exc_pc_mux_i;
	input wire [6:0] exc_cause;
	input wire dummy_instr_en_i;
	input wire [2:0] dummy_instr_mask_i;
	input wire dummy_instr_seed_en_i;
	input wire [31:0] dummy_instr_seed_i;
	input wire icache_enable_i;
	input wire icache_inval_i;
	output wire icache_ecc_error_o;
	input wire [31:0] branch_target_ex_i;
	input wire [31:0] csr_mepc_i;
	input wire [31:0] csr_depc_i;
	input wire [31:0] csr_mtvec_i;
	output wire csr_mtvec_init_o;
	input wire id_in_ready_i;
	output wire pc_mismatch_alert_o;
	output wire if_busy_o;
	wire instr_valid_id_d;
	reg instr_valid_id_q;
	wire instr_new_id_d;
	reg instr_new_id_q;
	wire instr_err;
	wire instr_intg_err;
	wire prefetch_busy;
	wire branch_req;
	reg [31:0] fetch_addr_n;
	wire unused_fetch_addr_n0;
	wire prefetch_branch;
	wire [31:0] prefetch_addr;
	wire fetch_valid_raw;
	wire fetch_valid;
	wire fetch_ready;
	wire [31:0] fetch_rdata;
	wire [31:0] fetch_addr;
	wire fetch_err;
	wire fetch_err_plus2;
	wire [31:0] instr_decompressed;
	wire illegal_c_insn;
	wire instr_is_compressed;
	wire [1:0] instr_gets_expanded;
	wire if_instr_valid;
	wire [31:0] if_instr_rdata;
	wire [31:0] if_instr_addr;
	wire if_instr_bus_err;
	wire if_instr_pmp_err;
	wire if_instr_err;
	wire if_instr_err_plus2;
	reg [31:0] exc_pc;
	wire if_id_pipe_reg_we;
	wire stall_dummy_instr;
	wire [31:0] instr_out;
	wire instr_is_compressed_out;
	wire [1:0] instr_gets_expanded_out;
	wire illegal_c_instr_out;
	wire instr_err_out;
	wire predict_branch_taken;
	wire [31:0] predict_branch_pc;
	reg [4:0] irq_vec;
	wire [2:0] pc_mux_internal;
	wire [7:0] unused_boot_addr;
	wire [7:0] unused_csr_mtvec;
	wire unused_exc_cause;
	assign unused_boot_addr = boot_addr_i[7:0];
	assign unused_csr_mtvec = csr_mtvec_i[7:0];
	assign unused_exc_cause = |{exc_cause[5], exc_cause[6]};
	localparam [6:0] ibex_pkg_ExcCauseIrqNm = 7'h3f;
	always @(*) begin : exc_pc_mux
		if (_sv2v_0)
			;
		irq_vec = exc_cause[4-:5];
		if (exc_cause[6])
			irq_vec = ibex_pkg_ExcCauseIrqNm[4-:5];
		(* full_case, parallel_case *)
		case (exc_pc_mux_i)
			2'd0: exc_pc = {csr_mtvec_i[31:8], 8'h00};
			2'd1: exc_pc = {csr_mtvec_i[31:8], 1'b0, irq_vec, 2'b00};
			2'd2: exc_pc = DmHaltAddr;
			2'd3: exc_pc = DmExceptionAddr;
			default: exc_pc = {csr_mtvec_i[31:8], 8'h00};
		endcase
	end
	assign pc_mux_internal = ((BranchPredictor && predict_branch_taken) && !pc_set_i ? 3'd5 : pc_mux_i);
	always @(*) begin : fetch_addr_mux
		if (_sv2v_0)
			;
		(* full_case, parallel_case *)
		case (pc_mux_internal)
			3'd0: fetch_addr_n = {boot_addr_i[31:8], 8'h80};
			3'd1: fetch_addr_n = branch_target_ex_i;
			3'd2: fetch_addr_n = exc_pc;
			3'd3: fetch_addr_n = csr_mepc_i;
			3'd4: fetch_addr_n = csr_depc_i;
			3'd5: fetch_addr_n = (BranchPredictor ? predict_branch_pc : {boot_addr_i[31:8], 8'h80});
			default: fetch_addr_n = {boot_addr_i[31:8], 8'h80};
		endcase
	end
	assign csr_mtvec_init_o = (pc_mux_i == 3'd0) & pc_set_i;
	generate
		if (MemECC) begin : g_mem_ecc
			wire [1:0] ecc_err;
			wire [MemDataWidth - 1:0] instr_rdata_buf;
			prim_buf #(.Width(MemDataWidth)) u_prim_buf_instr_rdata(
				.in_i(instr_rdata_i),
				.out_o(instr_rdata_buf)
			);
			prim_secded_inv_39_32_dec u_instr_intg_dec(
				.data_i(instr_rdata_buf),
				.data_o(),
				.syndrome_o(),
				.err_o(ecc_err)
			);
			assign instr_intg_err = |ecc_err;
		end
		else begin : g_no_mem_ecc
			assign instr_intg_err = 1'b0;
		end
	endgenerate
	assign instr_err = instr_intg_err | instr_bus_err_i;
	assign instr_intg_err_o = instr_intg_err & instr_rvalid_i;
	assign prefetch_branch = branch_req | nt_branch_mispredict_i;
	assign prefetch_addr = (branch_req ? {fetch_addr_n[31:1], 1'b0} : nt_branch_addr_i);
	assign fetch_valid = fetch_valid_raw & ~nt_branch_mispredict_i;
	generate
		if (ICache) begin : gen_icache
			ibex_icache #(
				.ICacheECC(ICacheECC),
				.ResetAll(ResetAll),
				.BusSizeECC(BusSizeECC),
				.TagSizeECC(TagSizeECC),
				.LineSizeECC(LineSizeECC),
				.TweakInfection(ICacheTweakInfection)
			) icache_i(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.req_i(req_i),
				.branch_i(prefetch_branch),
				.addr_i(prefetch_addr),
				.ready_i(fetch_ready),
				.valid_o(fetch_valid_raw),
				.rdata_o(fetch_rdata),
				.addr_o(fetch_addr),
				.err_o(fetch_err),
				.err_plus2_o(fetch_err_plus2),
				.instr_req_o(instr_req_o),
				.instr_addr_o(instr_addr_o),
				.instr_gnt_i(instr_gnt_i),
				.instr_rvalid_i(instr_rvalid_i),
				.instr_rdata_i(instr_rdata_i[31:0]),
				.instr_err_i(instr_err),
				.ic_tag_req_o(ic_tag_req_o),
				.ic_tag_write_o(ic_tag_write_o),
				.ic_tag_addr_o(ic_tag_addr_o),
				.ic_tag_wdata_o(ic_tag_wdata_o),
				.ic_tag_rdata_i(ic_tag_rdata_i),
				.ic_data_req_o(ic_data_req_o),
				.ic_data_write_o(ic_data_write_o),
				.ic_data_addr_o(ic_data_addr_o),
				.ic_data_wdata_o(ic_data_wdata_o),
				.ic_data_rdata_i(ic_data_rdata_i),
				.ic_scr_key_valid_i(ic_scr_key_valid_i),
				.ic_scr_key_req_o(ic_scr_key_req_o),
				.icache_enable_i(icache_enable_i),
				.icache_inval_i(icache_inval_i),
				.busy_o(prefetch_busy),
				.ecc_error_o(icache_ecc_error_o)
			);
		end
		else begin : gen_prefetch_buffer
			ibex_prefetch_buffer #(.ResetAll(ResetAll)) prefetch_buffer_i(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.req_i(req_i),
				.branch_i(prefetch_branch),
				.addr_i(prefetch_addr),
				.ready_i(fetch_ready),
				.valid_o(fetch_valid_raw),
				.rdata_o(fetch_rdata),
				.addr_o(fetch_addr),
				.err_o(fetch_err),
				.err_plus2_o(fetch_err_plus2),
				.instr_req_o(instr_req_o),
				.instr_addr_o(instr_addr_o),
				.instr_gnt_i(instr_gnt_i),
				.instr_rvalid_i(instr_rvalid_i),
				.instr_rdata_i(instr_rdata_i[31:0]),
				.instr_err_i(instr_err),
				.busy_o(prefetch_busy)
			);
			wire unused_icen;
			wire unused_icinv;
			wire unused_scr_key_valid;
			wire [(ibex_pkg_IC_NUM_WAYS * TagSizeECC) - 1:0] unused_tag_ram_input;
			wire [(ibex_pkg_IC_NUM_WAYS * LineSizeECC) - 1:0] unused_data_ram_input;
			assign unused_icen = icache_enable_i;
			assign unused_icinv = icache_inval_i;
			assign unused_tag_ram_input = ic_tag_rdata_i;
			assign unused_data_ram_input = ic_data_rdata_i;
			assign unused_scr_key_valid = ic_scr_key_valid_i;
			assign ic_tag_req_o = 'b0;
			assign ic_tag_write_o = 'b0;
			assign ic_tag_addr_o = 'b0;
			assign ic_tag_wdata_o = 'b0;
			assign ic_data_req_o = 'b0;
			assign ic_data_write_o = 'b0;
			assign ic_data_addr_o = 'b0;
			assign ic_data_wdata_o = 'b0;
			assign ic_scr_key_req_o = 'b0;
			assign icache_ecc_error_o = 'b0;
		end
	endgenerate
	assign unused_fetch_addr_n0 = fetch_addr_n[0];
	assign branch_req = pc_set_i | predict_branch_taken;
	assign pc_if_o = if_instr_addr;
	assign if_busy_o = prefetch_busy;
	assign if_instr_pmp_err = pmp_err_if_i | ((if_instr_addr[1] & ~instr_is_compressed) & pmp_err_if_plus2_i);
	assign if_instr_err = if_instr_bus_err | if_instr_pmp_err;
	assign if_instr_err_plus2 = (((if_instr_addr[1] & ~instr_is_compressed) & pmp_err_if_plus2_i) | fetch_err_plus2) & ~pmp_err_if_i;
	ibex_compressed_decoder #(
		.RV32ZC(RV32ZC),
		.ResetAll(ResetAll)
	) compressed_decoder_i(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.valid_i(fetch_valid & ~fetch_err),
		.id_in_ready_i(id_in_ready_i & ~pc_set_i),
		.instr_i(if_instr_rdata),
		.instr_o(instr_decompressed),
		.is_compressed_o(instr_is_compressed),
		.gets_expanded_o(instr_gets_expanded),
		.illegal_instr_o(illegal_c_insn)
	);
	generate
		if (DummyInstructions) begin : gen_dummy_instr
			wire insert_dummy_instr;
			wire [31:0] dummy_instr_data;
			ibex_dummy_instr #(
				.RndCnstLfsrSeed(RndCnstLfsrSeed),
				.RndCnstLfsrPerm(RndCnstLfsrPerm)
			) dummy_instr_i(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.dummy_instr_en_i(dummy_instr_en_i),
				.dummy_instr_mask_i(dummy_instr_mask_i),
				.dummy_instr_seed_en_i(dummy_instr_seed_en_i),
				.dummy_instr_seed_i(dummy_instr_seed_i),
				.fetch_valid_i(fetch_valid),
				.id_in_ready_i(id_in_ready_i),
				.insert_dummy_instr_o(insert_dummy_instr),
				.dummy_instr_data_o(dummy_instr_data)
			);
			assign instr_out = (insert_dummy_instr ? dummy_instr_data : instr_decompressed);
			assign instr_is_compressed_out = (insert_dummy_instr ? 1'b0 : instr_is_compressed);
			assign instr_gets_expanded_out = (insert_dummy_instr ? 2'd0 : instr_gets_expanded);
			assign illegal_c_instr_out = (insert_dummy_instr ? 1'b0 : illegal_c_insn);
			assign instr_err_out = (insert_dummy_instr ? 1'b0 : if_instr_err);
			assign stall_dummy_instr = insert_dummy_instr;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					dummy_instr_id_o <= 1'b0;
				else if (if_id_pipe_reg_we)
					dummy_instr_id_o <= insert_dummy_instr;
		end
		else begin : gen_no_dummy_instr
			wire unused_dummy_en;
			wire [2:0] unused_dummy_mask;
			wire unused_dummy_seed_en;
			wire [31:0] unused_dummy_seed;
			assign unused_dummy_en = dummy_instr_en_i;
			assign unused_dummy_mask = dummy_instr_mask_i;
			assign unused_dummy_seed_en = dummy_instr_seed_en_i;
			assign unused_dummy_seed = dummy_instr_seed_i;
			assign instr_out = instr_decompressed;
			assign instr_is_compressed_out = instr_is_compressed;
			assign instr_gets_expanded_out = instr_gets_expanded;
			assign illegal_c_instr_out = illegal_c_insn;
			assign instr_err_out = if_instr_err;
			assign stall_dummy_instr = 1'b0;
			wire [1:1] sv2v_tmp_C8A0C;
			assign sv2v_tmp_C8A0C = 1'b0;
			always @(*) dummy_instr_id_o = sv2v_tmp_C8A0C;
		end
	endgenerate
	assign instr_valid_id_d = ((if_instr_valid & id_in_ready_i) & ~pc_set_i) | (instr_valid_id_q & ~instr_valid_clear_i);
	assign instr_new_id_d = (if_instr_valid & id_in_ready_i) & ~pc_set_i;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni) begin
			instr_valid_id_q <= 1'b0;
			instr_new_id_q <= 1'b0;
		end
		else begin
			instr_valid_id_q <= instr_valid_id_d;
			instr_new_id_q <= instr_new_id_d;
		end
	assign instr_valid_id_o = instr_valid_id_q;
	assign instr_new_id_o = instr_new_id_q;
	assign if_id_pipe_reg_we = instr_new_id_d;
	generate
		if (ResetAll) begin : g_instr_rdata_ra
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni) begin
					instr_rdata_id_o <= 1'sb0;
					instr_rdata_alu_id_o <= 1'sb0;
					instr_fetch_err_o <= 1'sb0;
					instr_fetch_err_plus2_o <= 1'sb0;
					instr_rdata_c_id_o <= 1'sb0;
					instr_is_compressed_id_o <= 1'sb0;
					instr_gets_expanded_id_o <= 2'd0;
					instr_expanded_id_o <= 1'sb0;
					illegal_c_insn_id_o <= 1'sb0;
					pc_id_o <= 1'sb0;
				end
				else if (if_id_pipe_reg_we) begin
					instr_rdata_id_o <= instr_out;
					instr_rdata_alu_id_o <= instr_out;
					instr_fetch_err_o <= instr_err_out;
					instr_fetch_err_plus2_o <= if_instr_err_plus2;
					instr_rdata_c_id_o <= if_instr_rdata[15:0];
					instr_is_compressed_id_o <= instr_is_compressed_out;
					instr_gets_expanded_id_o <= instr_gets_expanded_out;
					instr_expanded_id_o <= if_instr_rdata[15:0];
					illegal_c_insn_id_o <= illegal_c_instr_out;
					pc_id_o <= pc_if_o;
				end
		end
		else begin : g_instr_rdata_nr
			always @(posedge clk_i)
				if (if_id_pipe_reg_we) begin
					instr_rdata_id_o <= instr_out;
					instr_rdata_alu_id_o <= instr_out;
					instr_fetch_err_o <= instr_err_out;
					instr_fetch_err_plus2_o <= if_instr_err_plus2;
					instr_rdata_c_id_o <= if_instr_rdata[15:0];
					instr_is_compressed_id_o <= instr_is_compressed_out;
					instr_gets_expanded_id_o <= instr_gets_expanded_out;
					instr_expanded_id_o <= if_instr_rdata[15:0];
					illegal_c_insn_id_o <= illegal_c_instr_out;
					pc_id_o <= pc_if_o;
				end
		end
		if (PCIncrCheck) begin : g_secure_pc
			wire [31:0] prev_instr_addr_incr;
			wire [31:0] prev_instr_addr_incr_buf;
			reg prev_instr_seq_q;
			wire prev_instr_seq_d;
			assign prev_instr_seq_d = ((((prev_instr_seq_q | instr_new_id_d) & ~branch_req) & ~if_instr_err) & ~stall_dummy_instr) & (instr_gets_expanded != 2'd1);
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					prev_instr_seq_q <= 1'b0;
				else
					prev_instr_seq_q <= prev_instr_seq_d;
			assign prev_instr_addr_incr = pc_id_o + (instr_is_compressed_id_o ? 32'd2 : 32'd4);
			prim_buf #(.Width(32)) u_prev_instr_addr_incr_buf(
				.in_i(prev_instr_addr_incr),
				.out_o(prev_instr_addr_incr_buf)
			);
			assign pc_mismatch_alert_o = prev_instr_seq_q & (pc_if_o != prev_instr_addr_incr_buf);
		end
		else begin : g_no_secure_pc
			assign pc_mismatch_alert_o = 1'b0;
		end
		if (BranchPredictor) begin : g_branch_predictor
			reg [31:0] instr_skid_data_q;
			reg [31:0] instr_skid_addr_q;
			reg instr_skid_bp_taken_q;
			reg instr_skid_valid_q;
			wire instr_skid_valid_d;
			wire instr_skid_en;
			reg instr_bp_taken_q;
			wire instr_bp_taken_d;
			wire predict_branch_taken_raw;
			if (ResetAll) begin : g_bp_taken_ra
				always @(posedge clk_i or negedge rst_ni)
					if (!rst_ni)
						instr_bp_taken_q <= 1'sb0;
					else if (if_id_pipe_reg_we)
						instr_bp_taken_q <= instr_bp_taken_d;
			end
			else begin : g_bp_taken_nr
				always @(posedge clk_i)
					if (if_id_pipe_reg_we)
						instr_bp_taken_q <= instr_bp_taken_d;
			end
			assign instr_skid_en = ((predict_branch_taken & ~pc_set_i) & ~id_in_ready_i) & ~instr_skid_valid_q;
			assign instr_skid_valid_d = (((instr_skid_valid_q & ~id_in_ready_i) & ~stall_dummy_instr) & (instr_gets_expanded != 2'd1)) | instr_skid_en;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					instr_skid_valid_q <= 1'b0;
				else
					instr_skid_valid_q <= instr_skid_valid_d;
			if (ResetAll) begin : g_instr_skid_ra
				always @(posedge clk_i or negedge rst_ni)
					if (!rst_ni) begin
						instr_skid_bp_taken_q <= 1'sb0;
						instr_skid_data_q <= 1'sb0;
						instr_skid_addr_q <= 1'sb0;
					end
					else if (instr_skid_en) begin
						instr_skid_bp_taken_q <= predict_branch_taken;
						instr_skid_data_q <= fetch_rdata;
						instr_skid_addr_q <= fetch_addr;
					end
			end
			else begin : g_instr_skid_nr
				always @(posedge clk_i)
					if (instr_skid_en) begin
						instr_skid_bp_taken_q <= predict_branch_taken;
						instr_skid_data_q <= fetch_rdata;
						instr_skid_addr_q <= fetch_addr;
					end
			end
			ibex_branch_predict branch_predict_i(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.fetch_rdata_i(fetch_rdata),
				.fetch_pc_i(fetch_addr),
				.fetch_valid_i(fetch_valid),
				.predict_branch_taken_o(predict_branch_taken_raw),
				.predict_branch_pc_o(predict_branch_pc)
			);
			assign predict_branch_taken = (predict_branch_taken_raw & ~instr_skid_valid_q) & ~fetch_err;
			assign if_instr_valid = fetch_valid | (instr_skid_valid_q & ~nt_branch_mispredict_i);
			assign if_instr_rdata = (instr_skid_valid_q ? instr_skid_data_q : fetch_rdata);
			assign if_instr_addr = (instr_skid_valid_q ? instr_skid_addr_q : fetch_addr);
			assign if_instr_bus_err = ~instr_skid_valid_q & fetch_err;
			assign instr_bp_taken_d = (instr_skid_valid_q ? instr_skid_bp_taken_q : predict_branch_taken);
			assign fetch_ready = ((id_in_ready_i & ~stall_dummy_instr) & (instr_gets_expanded != 2'd1)) & ~instr_skid_valid_q;
			assign instr_bp_taken_o = instr_bp_taken_q;
		end
		else begin : g_no_branch_predictor
			assign instr_bp_taken_o = 1'b0;
			assign predict_branch_taken = 1'b0;
			assign predict_branch_pc = 32'b00000000000000000000000000000000;
			assign if_instr_valid = fetch_valid;
			assign if_instr_rdata = fetch_rdata;
			assign if_instr_addr = fetch_addr;
			assign if_instr_bus_err = fetch_err;
			assign fetch_ready = (id_in_ready_i & ~stall_dummy_instr) & (instr_gets_expanded != 2'd1);
		end
	endgenerate
	initial _sv2v_0 = 0;
endmodule

module ibex_fetch_fifo (
	clk_i,
	rst_ni,
	clear_i,
	busy_o,
	in_valid_i,
	in_addr_i,
	in_rdata_i,
	in_err_i,
	out_valid_o,
	out_ready_i,
	out_addr_o,
	out_rdata_o,
	out_err_o,
	out_err_plus2_o
);
	reg _sv2v_0;
	parameter [31:0] NUM_REQS = 2;
	parameter [0:0] ResetAll = 1'b0;
	input wire clk_i;
	input wire rst_ni;
	input wire clear_i;
	output wire [NUM_REQS - 1:0] busy_o;
	input wire in_valid_i;
	input wire [31:0] in_addr_i;
	input wire [31:0] in_rdata_i;
	input wire in_err_i;
	output reg out_valid_o;
	input wire out_ready_i;
	output wire [31:0] out_addr_o;
	output reg [31:0] out_rdata_o;
	output reg out_err_o;
	output reg out_err_plus2_o;
	localparam [31:0] DEPTH = NUM_REQS + 1;
	wire [(DEPTH * 32) - 1:0] rdata_d;
	reg [(DEPTH * 32) - 1:0] rdata_q;
	wire [DEPTH - 1:0] err_d;
	reg [DEPTH - 1:0] err_q;
	wire [DEPTH - 1:0] valid_d;
	reg [DEPTH - 1:0] valid_q;
	wire [DEPTH - 1:0] lowest_free_entry;
	wire [DEPTH - 1:0] valid_pushed;
	wire [DEPTH - 1:0] valid_popped;
	wire [DEPTH - 1:0] entry_en;
	wire pop_fifo;
	wire [31:0] rdata;
	wire [31:0] rdata_unaligned;
	wire err;
	wire err_unaligned;
	wire err_plus2;
	wire valid;
	wire valid_unaligned;
	wire aligned_is_compressed;
	wire unaligned_is_compressed;
	wire addr_incr_two;
	wire [31:1] instr_addr_next;
	wire [31:1] instr_addr_d;
	reg [31:1] instr_addr_q;
	wire instr_addr_en;
	wire unused_addr_in;
	assign rdata = (valid_q[0] ? rdata_q[0+:32] : in_rdata_i);
	assign err = (valid_q[0] ? err_q[0] : in_err_i);
	assign valid = valid_q[0] | in_valid_i;
	assign rdata_unaligned = (valid_q[1] ? {rdata_q[47-:16], rdata[31:16]} : {in_rdata_i[15:0], rdata[31:16]});
	assign err_unaligned = (valid_q[1] ? (err_q[1] & ~unaligned_is_compressed) | err_q[0] : (valid_q[0] & err_q[0]) | (in_err_i & (~valid_q[0] | ~unaligned_is_compressed)));
	assign err_plus2 = (valid_q[1] ? err_q[1] & ~err_q[0] : (in_err_i & valid_q[0]) & ~err_q[0]);
	assign valid_unaligned = (valid_q[1] ? 1'b1 : valid_q[0] & in_valid_i);
	assign unaligned_is_compressed = (rdata[17:16] != 2'b11) & ~err;
	assign aligned_is_compressed = (rdata[1:0] != 2'b11) & ~err;
	always @(*) begin
		if (_sv2v_0)
			;
		if (out_addr_o[1]) begin
			out_rdata_o = rdata_unaligned;
			out_err_o = err_unaligned;
			out_err_plus2_o = err_plus2;
			if (unaligned_is_compressed)
				out_valid_o = valid;
			else
				out_valid_o = valid_unaligned;
		end
		else begin
			out_rdata_o = rdata;
			out_err_o = err;
			out_err_plus2_o = 1'b0;
			out_valid_o = valid;
		end
	end
	assign instr_addr_en = clear_i | (out_ready_i & out_valid_o);
	assign addr_incr_two = (instr_addr_q[1] ? unaligned_is_compressed : aligned_is_compressed);
	assign instr_addr_next = instr_addr_q[31:1] + {29'd0, ~addr_incr_two, addr_incr_two};
	assign instr_addr_d = (clear_i ? in_addr_i[31:1] : instr_addr_next);
	generate
		if (ResetAll) begin : g_instr_addr_ra
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					instr_addr_q <= 1'sb0;
				else if (instr_addr_en)
					instr_addr_q <= instr_addr_d;
		end
		else begin : g_instr_addr_nr
			always @(posedge clk_i)
				if (instr_addr_en)
					instr_addr_q <= instr_addr_d;
		end
	endgenerate
	assign out_addr_o = {instr_addr_q, 1'b0};
	assign unused_addr_in = in_addr_i[0];
	assign busy_o = valid_q[DEPTH - 1:DEPTH - NUM_REQS];
	assign pop_fifo = (out_ready_i & out_valid_o) & (~aligned_is_compressed | out_addr_o[1]);
	genvar _gv_i_1;
	generate
		for (_gv_i_1 = 0; _gv_i_1 < (DEPTH - 1); _gv_i_1 = _gv_i_1 + 1) begin : g_fifo_next
			localparam i = _gv_i_1;
			if (i == 0) begin : g_ent0
				assign lowest_free_entry[i] = ~valid_q[i];
			end
			else begin : g_ent_others
				assign lowest_free_entry[i] = ~valid_q[i] & valid_q[i - 1];
			end
			assign valid_pushed[i] = (in_valid_i & lowest_free_entry[i]) | valid_q[i];
			assign valid_popped[i] = (pop_fifo ? valid_pushed[i + 1] : valid_pushed[i]);
			assign valid_d[i] = valid_popped[i] & ~clear_i;
			assign entry_en[i] = (valid_pushed[i + 1] & pop_fifo) | ((in_valid_i & lowest_free_entry[i]) & ~pop_fifo);
			assign rdata_d[i * 32+:32] = (valid_q[i + 1] ? rdata_q[(i + 1) * 32+:32] : in_rdata_i);
			assign err_d[i] = (valid_q[i + 1] ? err_q[i + 1] : in_err_i);
		end
	endgenerate
	assign lowest_free_entry[DEPTH - 1] = ~valid_q[DEPTH - 1] & valid_q[DEPTH - 2];
	assign valid_pushed[DEPTH - 1] = valid_q[DEPTH - 1] | (in_valid_i & lowest_free_entry[DEPTH - 1]);
	assign valid_popped[DEPTH - 1] = (pop_fifo ? 1'b0 : valid_pushed[DEPTH - 1]);
	assign valid_d[DEPTH - 1] = valid_popped[DEPTH - 1] & ~clear_i;
	assign entry_en[DEPTH - 1] = in_valid_i & lowest_free_entry[DEPTH - 1];
	assign rdata_d[(DEPTH - 1) * 32+:32] = in_rdata_i;
	assign err_d[DEPTH - 1] = in_err_i;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			valid_q <= 1'sb0;
		else
			valid_q <= valid_d;
	genvar _gv_i_2;
	generate
		for (_gv_i_2 = 0; _gv_i_2 < DEPTH; _gv_i_2 = _gv_i_2 + 1) begin : g_fifo_regs
			localparam i = _gv_i_2;
			if (ResetAll) begin : g_rdata_ra
				always @(posedge clk_i or negedge rst_ni)
					if (!rst_ni) begin
						rdata_q[i * 32+:32] <= 1'sb0;
						err_q[i] <= 1'sb0;
					end
					else if (entry_en[i]) begin
						rdata_q[i * 32+:32] <= rdata_d[i * 32+:32];
						err_q[i] <= err_d[i];
					end
			end
			else begin : g_rdata_nr
				always @(posedge clk_i)
					if (entry_en[i]) begin
						rdata_q[i * 32+:32] <= rdata_d[i * 32+:32];
						err_q[i] <= err_d[i];
					end
			end
		end
	endgenerate
	initial _sv2v_0 = 0;
endmodule

module ibex_prefetch_buffer (
	clk_i,
	rst_ni,
	req_i,
	branch_i,
	addr_i,
	ready_i,
	valid_o,
	rdata_o,
	addr_o,
	err_o,
	err_plus2_o,
	instr_req_o,
	instr_gnt_i,
	instr_addr_o,
	instr_rdata_i,
	instr_err_i,
	instr_rvalid_i,
	busy_o
);
	parameter [0:0] ResetAll = 1'b0;
	input wire clk_i;
	input wire rst_ni;
	input wire req_i;
	input wire branch_i;
	input wire [31:0] addr_i;
	input wire ready_i;
	output wire valid_o;
	output wire [31:0] rdata_o;
	output wire [31:0] addr_o;
	output wire err_o;
	output wire err_plus2_o;
	output wire instr_req_o;
	input wire instr_gnt_i;
	output wire [31:0] instr_addr_o;
	input wire [31:0] instr_rdata_i;
	input wire instr_err_i;
	input wire instr_rvalid_i;
	output wire busy_o;
	localparam [31:0] NUM_REQS = 2;
	wire valid_new_req;
	wire valid_req;
	wire valid_req_d;
	reg valid_req_q;
	wire discard_req_d;
	reg discard_req_q;
	wire [1:0] rdata_outstanding_n;
	wire [1:0] rdata_outstanding_s;
	reg [1:0] rdata_outstanding_q;
	wire [1:0] branch_discard_n;
	wire [1:0] branch_discard_s;
	reg [1:0] branch_discard_q;
	wire [1:0] rdata_outstanding_rev;
	wire [31:0] stored_addr_d;
	reg [31:0] stored_addr_q;
	wire stored_addr_en;
	wire [31:0] fetch_addr_d;
	reg [31:0] fetch_addr_q;
	wire fetch_addr_en;
	wire [31:0] instr_addr;
	wire [31:0] instr_addr_w_aligned;
	wire fifo_valid;
	wire [31:0] fifo_addr;
	wire fifo_ready;
	wire fifo_clear;
	wire [1:0] fifo_busy;
	assign busy_o = |rdata_outstanding_q | instr_req_o;
	assign fifo_clear = branch_i;
	genvar _gv_i_3;
	generate
		for (_gv_i_3 = 0; _gv_i_3 < NUM_REQS; _gv_i_3 = _gv_i_3 + 1) begin : gen_rd_rev
			localparam i = _gv_i_3;
			assign rdata_outstanding_rev[i] = rdata_outstanding_q[1 - i];
		end
	endgenerate
	assign fifo_ready = ~&(fifo_busy | rdata_outstanding_rev);
	ibex_fetch_fifo #(
		.NUM_REQS(NUM_REQS),
		.ResetAll(ResetAll)
	) fifo_i(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.clear_i(fifo_clear),
		.busy_o(fifo_busy),
		.in_valid_i(fifo_valid),
		.in_addr_i(fifo_addr),
		.in_rdata_i(instr_rdata_i),
		.in_err_i(instr_err_i),
		.out_valid_o(valid_o),
		.out_ready_i(ready_i),
		.out_rdata_o(rdata_o),
		.out_addr_o(addr_o),
		.out_err_o(err_o),
		.out_err_plus2_o(err_plus2_o)
	);
	assign valid_new_req = (req_i & (fifo_ready | branch_i)) & ~rdata_outstanding_q[1];
	assign valid_req = valid_req_q | valid_new_req;
	assign valid_req_d = valid_req & ~instr_gnt_i;
	assign discard_req_d = valid_req_q & (branch_i | discard_req_q);
	assign stored_addr_en = (valid_new_req & ~valid_req_q) & ~instr_gnt_i;
	assign stored_addr_d = instr_addr;
	generate
		if (ResetAll) begin : g_stored_addr_ra
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					stored_addr_q <= 1'sb0;
				else if (stored_addr_en)
					stored_addr_q <= stored_addr_d;
		end
		else begin : g_stored_addr_nr
			always @(posedge clk_i)
				if (stored_addr_en)
					stored_addr_q <= stored_addr_d;
		end
	endgenerate
	assign fetch_addr_en = branch_i | (valid_new_req & ~valid_req_q);
	assign fetch_addr_d = (branch_i ? addr_i : {fetch_addr_q[31:2], 2'b00}) + {{29 {1'b0}}, valid_new_req & ~valid_req_q, 2'b00};
	generate
		if (ResetAll) begin : g_fetch_addr_ra
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					fetch_addr_q <= 1'sb0;
				else if (fetch_addr_en)
					fetch_addr_q <= fetch_addr_d;
		end
		else begin : g_fetch_addr_nr
			always @(posedge clk_i)
				if (fetch_addr_en)
					fetch_addr_q <= fetch_addr_d;
		end
	endgenerate
	assign instr_addr = (valid_req_q ? stored_addr_q : (branch_i ? addr_i : fetch_addr_q));
	assign instr_addr_w_aligned = {instr_addr[31:2], 2'b00};
	genvar _gv_i_4;
	generate
		for (_gv_i_4 = 0; _gv_i_4 < NUM_REQS; _gv_i_4 = _gv_i_4 + 1) begin : g_outstanding_reqs
			localparam i = _gv_i_4;
			if (i == 0) begin : g_req0
				assign rdata_outstanding_n[i] = (valid_req & instr_gnt_i) | rdata_outstanding_q[i];
				assign branch_discard_n[i] = (((valid_req & instr_gnt_i) & discard_req_d) | (branch_i & rdata_outstanding_q[i])) | branch_discard_q[i];
			end
			else begin : g_reqtop
				assign rdata_outstanding_n[i] = ((valid_req & instr_gnt_i) & rdata_outstanding_q[i - 1]) | rdata_outstanding_q[i];
				assign branch_discard_n[i] = ((((valid_req & instr_gnt_i) & discard_req_d) & rdata_outstanding_q[i - 1]) | (branch_i & rdata_outstanding_q[i])) | branch_discard_q[i];
			end
		end
	endgenerate
	assign rdata_outstanding_s = (instr_rvalid_i ? {1'b0, rdata_outstanding_n[1:1]} : rdata_outstanding_n);
	assign branch_discard_s = (instr_rvalid_i ? {1'b0, branch_discard_n[1:1]} : branch_discard_n);
	assign fifo_valid = instr_rvalid_i & ~branch_discard_q[0];
	assign fifo_addr = addr_i;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni) begin
			valid_req_q <= 1'b0;
			discard_req_q <= 1'b0;
			rdata_outstanding_q <= 'b0;
			branch_discard_q <= 'b0;
		end
		else begin
			valid_req_q <= valid_req_d;
			discard_req_q <= discard_req_d;
			rdata_outstanding_q <= rdata_outstanding_s;
			branch_discard_q <= branch_discard_s;
		end
	assign instr_req_o = valid_req;
	assign instr_addr_o = instr_addr_w_aligned;
endmodule

module ibex_compressed_decoder (
	clk_i,
	rst_ni,
	valid_i,
	id_in_ready_i,
	instr_i,
	instr_o,
	is_compressed_o,
	gets_expanded_o,
	illegal_instr_o
);
	reg _sv2v_0;
	parameter integer RV32ZC = 32'sd3;
	parameter [0:0] ResetAll = 1'b0;
	input wire clk_i;
	input wire rst_ni;
	input wire valid_i;
	input wire id_in_ready_i;
	input wire [31:0] instr_i;
	output reg [31:0] instr_o;
	output wire is_compressed_o;
	output wire [1:0] gets_expanded_o;
	output reg illegal_instr_o;
	generate
		if (!((RV32ZC == 32'sd3) || (RV32ZC == 32'sd2))) begin : gen_unused_valid
			wire unused_valid;
			wire unused_id_in_ready;
			assign unused_valid = valid_i;
			assign unused_id_in_ready = id_in_ready_i;
		end
	endgenerate
	function automatic [6:0] cm_stack_adj_base;
		input reg [3:0] rlist;
		(* full_case, parallel_case *)
		case (rlist)
			4'd4, 4'd5, 4'd6, 4'd7: cm_stack_adj_base = 7'd16;
			4'd8, 4'd9, 4'd10, 4'd11: cm_stack_adj_base = 7'd32;
			4'd12, 4'd13, 4'd14: cm_stack_adj_base = 7'd48;
			4'd15: cm_stack_adj_base = 7'd64;
			default: cm_stack_adj_base = 7'd0;
		endcase
	endfunction
	function automatic [6:0] cm_stack_adj;
		input reg [3:0] rlist;
		input reg [1:0] spimm;
		cm_stack_adj = cm_stack_adj_base(rlist) + (spimm * 16);
	endfunction
	function automatic [4:0] cm_stack_adj_word;
		input reg [3:0] rlist;
		input reg [1:0] spimm;
		reg [6:0] tmp;
		reg [1:0] unused_tmp;
		begin
			tmp = cm_stack_adj(rlist, spimm);
			unused_tmp = tmp[1:0];
			cm_stack_adj_word = tmp[6:2];
		end
	endfunction
	function automatic [4:0] cm_rlist_top_reg;
		input reg [4:0] rlist;
		(* full_case, parallel_case *)
		case (rlist)
			5'd16, 5'd15, 5'd14, 5'd13, 5'd12, 5'd11, 5'd10, 5'd9, 5'd8, 5'd7: cm_rlist_top_reg = 5'd11 + rlist;
			5'd6, 5'd5: cm_rlist_top_reg = 5'd3 + rlist;
			5'd4: cm_rlist_top_reg = 5'd1;
			default: cm_rlist_top_reg = 5'd0;
		endcase
	endfunction
	function automatic [31:0] cm_push_store_reg;
		input reg [4:0] rlist;
		input reg [4:0] sp_offset;
		reg [11:0] neg_offset;
		reg signed [11:0] neg_offset_signed;
		reg [31:0] instr;
		begin
			neg_offset_signed = -$signed({5'b00000, sp_offset, 2'b00});
			neg_offset = $unsigned(neg_offset_signed);
			instr[6:0] = 7'h23;
			instr[11:7] = neg_offset[4:0];
			instr[14:12] = 3'b010;
			instr[19:15] = 5'd2;
			instr[24:20] = cm_rlist_top_reg(rlist);
			instr[31:25] = neg_offset[11:5];
			cm_push_store_reg = instr;
		end
	endfunction
	function automatic [31:0] cm_pop_load_reg;
		input reg [4:0] rlist;
		input reg [4:0] sp_offset;
		reg [31:0] instr;
		begin
			instr[6:0] = 7'h03;
			instr[11:7] = cm_rlist_top_reg(rlist);
			instr[14:12] = 3'b010;
			instr[19:15] = 5'd2;
			instr[31:20] = {5'b00000, sp_offset, 2'b00};
			cm_pop_load_reg = instr;
		end
	endfunction
	function automatic [31:0] cm_sp_addi;
		input reg [3:0] rlist;
		input reg [1:0] spimm;
		input reg decr;
		reg [11:0] imm;
		reg signed [11:0] imm_signed;
		reg [31:0] instr;
		begin
			decr = 1'b0;
			imm[11:7] = 1'sb0;
			imm[6:0] = cm_stack_adj(rlist, spimm);
			imm_signed = (decr ? -$signed(imm) : $signed(imm));
			instr[6:0] = 7'h13;
			instr[11:7] = 5'd2;
			instr[14:12] = 3'b000;
			instr[19:15] = 5'd2;
			instr[31:20] = $unsigned(imm_signed);
			cm_sp_addi = instr;
		end
	endfunction
	function automatic [31:0] cm_mv_reg;
		input reg [4:0] src;
		input reg [4:0] dst;
		reg [31:0] instr;
		begin
			instr[6:0] = 7'h13;
			instr[11:7] = dst;
			instr[14:12] = 3'b000;
			instr[19:15] = src;
			instr[31:20] = 12'd0;
			cm_mv_reg = instr;
		end
	endfunction
	function automatic [31:0] cm_zero_a0;
		input reg _sv2v_unused;
		cm_zero_a0 = cm_mv_reg(5'd0, 5'd10);
	endfunction
	function automatic [31:0] cm_ret_ra;
		input reg _sv2v_unused;
		reg [31:0] instr;
		begin
			instr[6:0] = 7'h67;
			instr[11:7] = 5'd0;
			instr[14:12] = 3'b000;
			instr[19:15] = 5'd1;
			instr[31:20] = 12'd0;
			cm_ret_ra = instr;
		end
	endfunction
	function automatic [31:0] cm_mvsa01;
		input reg a01;
		input reg [2:0] rs;
		reg [4:0] src;
		reg [4:0] dst;
		begin
			src = 5'd10 + {4'd0, a01};
			dst = {rs[2:1] > 2'd0, rs[2:1] == 2'd0, rs[2:0]};
			cm_mvsa01 = cm_mv_reg(src, dst);
		end
	endfunction
	function automatic [31:0] cm_mva01s;
		input reg [2:0] rs;
		input reg a01;
		reg [4:0] src;
		reg [4:0] dst;
		begin
			src = {rs[2:1] > 2'd0, rs[2:1] == 2'd0, rs[2:0]};
			dst = 5'd10 + {4'd0, a01};
			cm_mva01s = cm_mv_reg(src, dst);
		end
	endfunction
	function automatic [4:0] cm_rlist_init;
		input reg [3:0] instr_rlist;
		reg [4:0] rlist;
		begin
			rlist = {1'b0, instr_rlist};
			if (rlist == 5'd15)
				rlist = 5'd16;
			cm_rlist_init = rlist;
		end
	endfunction
	reg [4:0] cm_rlist_d;
	reg [4:0] cm_rlist_q;
	reg [4:0] cm_sp_offset_d;
	reg [4:0] cm_sp_offset_q;
	reg [2:0] cm_state_d;
	reg [2:0] cm_state_q;
	reg [1:0] gets_expanded;
	generate
		if ((RV32ZC == 32'sd3) || (RV32ZC == 32'sd2)) begin : gen_gets_expanded
			assign gets_expanded_o = (valid_i ? gets_expanded : 2'd0);
		end
		else begin : gen_gets_expanded
			assign gets_expanded_o = gets_expanded;
		end
	endgenerate
	always @(*) begin
		if (_sv2v_0)
			;
		instr_o = instr_i;
		illegal_instr_o = 1'b0;
		gets_expanded = 2'd0;
		cm_rlist_d = cm_rlist_q;
		cm_sp_offset_d = cm_sp_offset_q;
		cm_state_d = cm_state_q;
		(* full_case, parallel_case *)
		case (instr_i[1:0])
			2'b00:
				(* full_case, parallel_case *)
				case (instr_i[15:13])
					3'b000: begin
						instr_o = {2'b00, instr_i[10:7], instr_i[12:11], instr_i[5], instr_i[6], 12'h041, instr_i[4:2], 7'h13};
						if (instr_i[12:5] == 8'b00000000)
							illegal_instr_o = 1'b1;
					end
					3'b010: instr_o = {5'b00000, instr_i[5], instr_i[12:10], instr_i[6], 4'b0001, instr_i[9:7], 5'b01001, instr_i[4:2], 7'h03};
					3'b110: instr_o = {5'b00000, instr_i[5], instr_i[12], 2'b01, instr_i[4:2], 2'b01, instr_i[9:7], 3'b010, instr_i[11:10], instr_i[6], 9'h023};
					3'b100:
						if ((RV32ZC == 32'sd3) || (RV32ZC == 32'sd1))
							(* full_case, parallel_case *)
							case (instr_i[12:10])
								3'b000: instr_o = {10'b0000000000, instr_i[5], instr_i[6], 2'b01, instr_i[9:7], 5'b10001, instr_i[4:2], 7'h03};
								3'b001:
									(* full_case, parallel_case *)
									case (instr_i[6])
										1'b0: instr_o = {10'b0000000000, instr_i[5], 3'b001, instr_i[9:7], 5'b10101, instr_i[4:2], 7'h03};
										1'b1: instr_o = {10'b0000000000, instr_i[5], 3'b001, instr_i[9:7], 5'b00101, instr_i[4:2], 7'h03};
										default: illegal_instr_o = 1'b1;
									endcase
								3'b010: instr_o = {9'b000000001, instr_i[4:2], 2'b01, instr_i[9:7], 6'b000000, instr_i[5], instr_i[6], 7'h23};
								3'b011:
									(* full_case, parallel_case *)
									case (instr_i[6])
										1'b0: instr_o = {9'b000000001, instr_i[4:2], 2'b01, instr_i[9:7], 6'b001000, instr_i[5], 8'h23};
										1'b1: illegal_instr_o = 1'b1;
										default: illegal_instr_o = 1'b1;
									endcase
								default: illegal_instr_o = 1'b1;
							endcase
						else
							illegal_instr_o = 1'b1;
					3'b001, 3'b011, 3'b101, 3'b111: illegal_instr_o = 1'b1;
					default: illegal_instr_o = 1'b1;
				endcase
			2'b01:
				(* full_case, parallel_case *)
				case (instr_i[15:13])
					3'b000: instr_o = {{6 {instr_i[12]}}, instr_i[12], instr_i[6:2], instr_i[11:7], 3'b000, instr_i[11:7], 7'h13};
					3'b001, 3'b101: instr_o = {instr_i[12], instr_i[8], instr_i[10:9], instr_i[6], instr_i[7], instr_i[2], instr_i[11], instr_i[5:3], {9 {instr_i[12]}}, 4'b0000, ~instr_i[15], 7'h6f};
					3'b010: instr_o = {{6 {instr_i[12]}}, instr_i[12], instr_i[6:2], 8'b00000000, instr_i[11:7], 7'h13};
					3'b011: begin
						instr_o = {{15 {instr_i[12]}}, instr_i[6:2], instr_i[11:7], 7'h37};
						if (instr_i[11:7] == 5'h02)
							instr_o = {{3 {instr_i[12]}}, instr_i[4:3], instr_i[5], instr_i[2], instr_i[6], 24'h010113};
						if ({instr_i[12], instr_i[6:2]} == 6'b000000)
							illegal_instr_o = 1'b1;
					end
					3'b100:
						(* full_case, parallel_case *)
						case (instr_i[11:10])
							2'b00, 2'b01: begin
								instr_o = {1'b0, instr_i[10], 5'b00000, instr_i[6:2], 2'b01, instr_i[9:7], 5'b10101, instr_i[9:7], 7'h13};
								if (instr_i[12] == 1'b1)
									illegal_instr_o = 1'b1;
							end
							2'b10: instr_o = {{6 {instr_i[12]}}, instr_i[12], instr_i[6:2], 2'b01, instr_i[9:7], 5'b11101, instr_i[9:7], 7'h13};
							2'b11:
								(* full_case, parallel_case *)
								case ({instr_i[12], instr_i[6:5]})
									3'b000: instr_o = {9'b010000001, instr_i[4:2], 2'b01, instr_i[9:7], 5'b00001, instr_i[9:7], 7'h33};
									3'b001: instr_o = {9'b000000001, instr_i[4:2], 2'b01, instr_i[9:7], 5'b10001, instr_i[9:7], 7'h33};
									3'b010: instr_o = {9'b000000001, instr_i[4:2], 2'b01, instr_i[9:7], 5'b11001, instr_i[9:7], 7'h33};
									3'b011: instr_o = {9'b000000001, instr_i[4:2], 2'b01, instr_i[9:7], 5'b11101, instr_i[9:7], 7'h33};
									3'b100, 3'b101: illegal_instr_o = 1'b1;
									3'b110:
										if ((RV32ZC == 32'sd3) || (RV32ZC == 32'sd1))
											instr_o = {9'b000000101, instr_i[4:2], 2'b01, instr_i[9:7], 5'b00001, instr_i[9:7], 7'h33};
										else
											illegal_instr_o = 1'b1;
									3'b111:
										if ((RV32ZC == 32'sd3) || (RV32ZC == 32'sd1))
											(* full_case, parallel_case *)
											case ({instr_i[4:2]})
												3'b000: instr_o = {14'h03fd, instr_i[9:7], 5'b11101, instr_i[9:7], 7'h13};
												3'b001: instr_o = {14'b01100000010001, instr_i[9:7], 5'b00101, instr_i[9:7], 7'h13};
												3'b010: instr_o = {14'b00001000000001, instr_i[9:7], 5'b10001, instr_i[9:7], 7'h33};
												3'b011: instr_o = {14'b01100000010101, instr_i[9:7], 5'b00101, instr_i[9:7], 7'h13};
												3'b100: illegal_instr_o = 1'b1;
												3'b101: instr_o = {14'h3ffd, instr_i[9:7], 5'b10001, instr_i[9:7], 7'h13};
												default: illegal_instr_o = 1'b1;
											endcase
										else
											illegal_instr_o = 1'b1;
									default: illegal_instr_o = 1'b1;
								endcase
							default: illegal_instr_o = 1'b1;
						endcase
					3'b110, 3'b111: instr_o = {{4 {instr_i[12]}}, instr_i[6:5], instr_i[2], 7'b0000001, instr_i[9:7], 2'b00, instr_i[13], instr_i[11:10], instr_i[4:3], instr_i[12], 7'h63};
					default: illegal_instr_o = 1'b1;
				endcase
			2'b10:
				(* full_case, parallel_case *)
				case (instr_i[15:13])
					3'b000: begin
						instr_o = {7'b0000000, instr_i[6:2], instr_i[11:7], 3'b001, instr_i[11:7], 7'h13};
						if (instr_i[12] == 1'b1)
							illegal_instr_o = 1'b1;
					end
					3'b010: begin
						instr_o = {4'b0000, instr_i[3:2], instr_i[12], instr_i[6:4], 10'h012, instr_i[11:7], 7'h03};
						if (instr_i[11:7] == 5'b00000)
							illegal_instr_o = 1'b1;
					end
					3'b100:
						if (instr_i[12] == 1'b0) begin
							if (instr_i[6:2] != 5'b00000)
								instr_o = {7'b0000000, instr_i[6:2], 8'b00000000, instr_i[11:7], 7'h33};
							else begin
								instr_o = {12'b000000000000, instr_i[11:7], 15'h0067};
								if (instr_i[11:7] == 5'b00000)
									illegal_instr_o = 1'b1;
							end
						end
						else if (instr_i[6:2] != 5'b00000)
							instr_o = {7'b0000000, instr_i[6:2], instr_i[11:7], 3'b000, instr_i[11:7], 7'h33};
						else if (instr_i[11:7] == 5'b00000)
							instr_o = 32'h00100073;
						else
							instr_o = {12'b000000000000, instr_i[11:7], 15'h00e7};
					3'b101:
						if ((RV32ZC == 32'sd3) || (RV32ZC == 32'sd2))
							(* full_case, parallel_case *)
							casez (instr_i[12:8])
								5'b11000: begin
									gets_expanded = 2'd1;
									(* full_case, parallel_case *)
									case (cm_state_q)
										3'd0: begin
											cm_rlist_d = cm_rlist_init(instr_i[7:4]);
											instr_o = cm_push_store_reg(cm_rlist_d, 5'd1);
											if (cm_rlist_d <= 5'd3)
												illegal_instr_o = 1'b1;
											else if (cm_rlist_d == 5'd4) begin
												if (valid_i && id_in_ready_i)
													cm_state_d = 3'd2;
											end
											else begin
												cm_rlist_d = cm_rlist_d - 5'd1;
												cm_sp_offset_d = 5'd2;
												if (valid_i && id_in_ready_i)
													cm_state_d = 3'd1;
											end
										end
										3'd1: begin
											instr_o = cm_push_store_reg(cm_rlist_q, cm_sp_offset_q);
											if (id_in_ready_i) begin
												cm_rlist_d = cm_rlist_q - 5'd1;
												cm_sp_offset_d = cm_sp_offset_q + 5'd1;
												if (cm_rlist_q == 5'd4)
													cm_state_d = 3'd2;
											end
										end
										3'd2: begin
											instr_o = cm_sp_addi(instr_i[7:4], instr_i[3:2], 1'b1);
											if (id_in_ready_i) begin
												gets_expanded = 2'd2;
												cm_state_d = 3'd0;
											end
										end
										default: cm_state_d = 3'd0;
									endcase
								end
								5'b11010, 5'b11100, 5'b11110: begin
									gets_expanded = 2'd1;
									(* full_case, parallel_case *)
									case (cm_state_q)
										3'd0: begin
											cm_rlist_d = cm_rlist_init(instr_i[7:4]);
											cm_sp_offset_d = cm_stack_adj_word(instr_i[7:4], instr_i[3:2]) - 5'd1;
											instr_o = cm_pop_load_reg(cm_rlist_d, cm_sp_offset_d);
											if (cm_rlist_d <= 5'd3)
												illegal_instr_o = 1'b1;
											else if (cm_rlist_d == 5'd4) begin
												if (valid_i && id_in_ready_i)
													cm_state_d = 3'd4;
											end
											else begin
												cm_rlist_d = cm_rlist_d - 5'd1;
												cm_sp_offset_d = cm_sp_offset_d - 5'd1;
												if (valid_i && id_in_ready_i)
													cm_state_d = 3'd3;
											end
										end
										3'd3: begin
											instr_o = cm_pop_load_reg(cm_rlist_q, cm_sp_offset_q);
											if (id_in_ready_i) begin
												cm_rlist_d = cm_rlist_q - 5'd1;
												cm_sp_offset_d = cm_sp_offset_q - 5'd1;
												if (cm_rlist_q == 5'd4)
													cm_state_d = 3'd4;
											end
										end
										3'd4: begin
											instr_o = cm_sp_addi(instr_i[7:4], instr_i[3:2], 1'b0);
											if (id_in_ready_i)
												(* full_case, parallel_case *)
												case (instr_i[12:8])
													5'b11100: cm_state_d = 3'd5;
													5'b11110: cm_state_d = 3'd6;
													default: begin
														gets_expanded = 2'd2;
														cm_state_d = 3'd0;
													end
												endcase
										end
										3'd5: begin
											instr_o = cm_zero_a0(0);
											if (id_in_ready_i)
												cm_state_d = 3'd6;
										end
										3'd6: begin
											instr_o = cm_ret_ra(0);
											if (id_in_ready_i) begin
												gets_expanded = 2'd2;
												cm_state_d = 3'd0;
											end
										end
										default: cm_state_d = 3'd0;
									endcase
								end
								5'b011zz:
									(* full_case, parallel_case *)
									case (instr_i[6:5])
										2'b01: begin
											gets_expanded = 2'd1;
											(* full_case, parallel_case *)
											case (cm_state_q)
												3'd0: begin
													instr_o = cm_mvsa01(1'b0, instr_i[9:7]);
													if (valid_i && id_in_ready_i)
														cm_state_d = 3'd7;
												end
												3'd7: begin
													instr_o = cm_mvsa01(1'b1, instr_i[4:2]);
													if (id_in_ready_i) begin
														gets_expanded = 2'd2;
														cm_state_d = 3'd0;
													end
												end
												default: cm_state_d = 3'd0;
											endcase
										end
										2'b11: begin
											gets_expanded = 2'd1;
											(* full_case, parallel_case *)
											case (cm_state_q)
												3'd0: begin
													instr_o = cm_mva01s(instr_i[9:7], 1'b0);
													if (valid_i && id_in_ready_i)
														cm_state_d = 3'd7;
												end
												3'd7: begin
													instr_o = cm_mva01s(instr_i[4:2], 1'b1);
													if (id_in_ready_i) begin
														gets_expanded = 2'd2;
														cm_state_d = 3'd0;
													end
												end
												default: cm_state_d = 3'd0;
											endcase
										end
										default: illegal_instr_o = 1'b1;
									endcase
								default: illegal_instr_o = 1'b1;
							endcase
						else
							illegal_instr_o = 1'b1;
					3'b110: instr_o = {4'b0000, instr_i[8:7], instr_i[12], instr_i[6:2], 8'h12, instr_i[11:9], 9'h023};
					3'b001, 3'b011, 3'b111: illegal_instr_o = 1'b1;
					default: illegal_instr_o = 1'b1;
				endcase
			2'b11: begin end
			default: illegal_instr_o = 1'b1;
		endcase
	end
	assign is_compressed_o = instr_i[1:0] != 2'b11;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			cm_state_q <= 3'd0;
		else
			cm_state_q <= cm_state_d;
	generate
		if (ResetAll) begin : g_cm_meta_ra
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni) begin
					cm_rlist_q <= 1'sb0;
					cm_sp_offset_q <= 1'sb0;
				end
				else begin
					cm_rlist_q <= cm_rlist_d;
					cm_sp_offset_q <= cm_sp_offset_d;
				end
		end
		else begin : g_cm_meta_nr
			always @(posedge clk_i) begin
				cm_rlist_q <= cm_rlist_d;
				cm_sp_offset_q <= cm_sp_offset_d;
			end
		end
	endgenerate
	initial _sv2v_0 = 0;
endmodule
