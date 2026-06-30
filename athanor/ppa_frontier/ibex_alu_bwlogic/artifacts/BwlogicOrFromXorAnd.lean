import Std.Tactic.BVDecide

open BitVec

theorem bwlogic_or_from_xor_and_u32 (a b : BitVec 32) :
    a ||| b = (a ^^^ b) ^^^ (a &&& b) := by
  bv_decide

theorem bwlogic_or_from_xor_and_u64 (a b : BitVec 64) :
    a ||| b = (a ^^^ b) ^^^ (a &&& b) := by
  bv_decide
