import Std.Tactic.BVDecide

/-
  Design-specific Lean receipt for the ibex_compressed_decoder Zcmp rlist
  initialization helper rewrite.

  The RTL helper maps the 4-bit compressed instruction rlist field into the
  internal 5-bit Zcmp rlist value. The only special case is 15 -> 16. The
  synthesis-facing candidate replaces the branch with a predicated increment:

    {1'b0, instr_rlist} + {4'b0000, instr_rlist == 4'd15}

  This proves only the local helper identity. The full compressed decoder still
  requires a sequential equivalence harness over cm_state_q, cm_rlist_q, and
  cm_sp_offset_q before the candidate can become accepted PPA evidence.
-/

namespace Kairos.ConeEquiv.IbexCompressedDecoderRlistInit

def originalRlistInit (instrRlist : BitVec 4) : BitVec 5 :=
  let rlist : BitVec 5 := instrRlist.setWidth 5
  if rlist == 15#5 then 16#5 else rlist

def rewrittenRlistInit (instrRlist : BitVec 4) : BitVec 5 :=
  instrRlist.setWidth 5 + if instrRlist == 15#4 then 1#5 else 0#5

theorem rlist_init_formula_equiv (instrRlist : BitVec 4) :
    originalRlistInit instrRlist = rewrittenRlistInit instrRlist := by
  unfold originalRlistInit rewrittenRlistInit
  bv_decide

theorem rlist_init_formula_preserves_low_values
    (instrRlist : BitVec 4) :
    instrRlist != 15#4 ->
      rewrittenRlistInit instrRlist = instrRlist.setWidth 5 := by
  unfold rewrittenRlistInit
  bv_decide

theorem rlist_init_formula_maps_fifteen :
    rewrittenRlistInit 15#4 = 16#5 := by
  unfold rewrittenRlistInit
  bv_decide

end Kairos.ConeEquiv.IbexCompressedDecoderRlistInit
