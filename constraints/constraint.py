import abc
import cvxpy.settings
import cvxpy.interface.matrix_utilities as intf
from cvxpy.expressions.operators import BinaryOperator
from affine import AffEqConstraint, AffLeqConstraint
import cvxpy.expressions.types as types

class Constraint(BinaryOperator):
    """
    A constraint on an optimization problem of the form
    affine == affine or affine <= affine.
    Stored internally as affine <=/== 0.
    """
    __metaclass__ = abc.ABCMeta
    # lh_exp - the left hand side of the constraint.
    # rh_exp - the right hand side of the constraint.
    # value_matrix - the matrix class for storing the dual value.
    # parent - the constraint that produced this constraint as part
    #          of canonicalization.
    def __init__(self, lh_exp, rh_exp, value_matrix=intf.DENSE_TARGET):
        super(Constraint, self).__init__(lh_exp, rh_exp)
        self.value_matrix = value_matrix
        self.interface = intf.get_matrix_interface(self.value_matrix)
        self._expr = (self.lh_exp - self.rh_exp)
        self._expr_obj,self._expr_constr = self._expr.canonical_form()

    def __repr__(self):
        return self.name()

    @property
    def size(self):
        return self._expr.size

    # The value of the dual variable.
    @property
    def dual(self):
        return self.dual_value

class EqConstraint(Constraint):
    OP_NAME = "=="
    # Both sides must be affine.
    def is_dcp(self):
        return self._expr.curvature.is_affine()

    # TODO expanding equality constraints.
    # Verify doesn't affect dual variables.
    def canonicalize(self):
        dual_holder = AffEqConstraint(self._expr_obj, 0, self.value_matrix, self)
        return (None, [dual_holder] + self._expr_constr)

class LeqConstraint(Constraint):
    OP_NAME = "<="
    # Left hand expression must be convex and right hand must be concave.
    def is_dcp(self):
        return self._expr.curvature.is_convex()

    # Replace inequality with an equality with slack.
    def canonicalize(self):
        slack = types.variable()(*self._expr_obj.size)
        slack_equality = AffEqConstraint(self._expr_obj, -slack, 
                                         self.value_matrix, self)
        slack_ineq = AffLeqConstraint(0, slack)
        constraints = self._expr_constr + [slack_equality, slack_ineq]
        return (None, constraints)