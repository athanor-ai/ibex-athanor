import Std.Tactic.BVDecide

/-
  Design-specific Lean receipt for the ibex decoder mult/div selector predicate
  rewrite. The selector is {instr_alu[31:25], instr_alu[14:12]}.
-/

namespace Athanor.Frontier.IbexDecoderMultdivPredicate

def mult_case (sel : BitVec 10) : Bool :=
  sel == 0b0000001000#10 ||
  sel == 0b0000001001#10 ||
  sel == 0b0000001010#10 ||
  sel == 0b0000001011#10

def div_case (sel : BitVec 10) : Bool :=
  sel == 0b0000001100#10 ||
  sel == 0b0000001101#10 ||
  sel == 0b0000001110#10 ||
  sel == 0b0000001111#10

def mult_predicate (sel : BitVec 10) : Bool :=
  (sel &&& 0b1111111000#10) == 0b0000001000#10 &&
  (sel &&& 0b0000000100#10) == 0#10

def div_predicate (sel : BitVec 10) : Bool :=
  (sel &&& 0b1111111000#10) == 0b0000001000#10 &&
  (sel &&& 0b0000000100#10) == 0b0000000100#10

theorem mult_sel_predicate_equiv (sel : BitVec 10) :
    mult_case sel = mult_predicate sel := by
  unfold mult_case mult_predicate
  bv_decide

theorem div_sel_predicate_equiv (sel : BitVec 10) :
    div_case sel = div_predicate sel := by
  unfold div_case div_predicate
  bv_decide

theorem mult_div_mutually_exclusive (sel : BitVec 10) :
    ¬ (mult_predicate sel = true ∧ div_predicate sel = true) := by
  unfold mult_predicate div_predicate
  bv_decide

end Athanor.Frontier.IbexDecoderMultdivPredicate
