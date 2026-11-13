"""Elaboration of tuples: their components, type components, and labels, and
the declarations a tuple's bindings make (a type group, a recursive or
simultaneous group of values).

The self-hosted counterpart is questlang/typechecker/tuples."""

from __future__ import annotations

from typing import Optional

import quest.syntax.ast as ast
from quest.typechecker.checker import Checker
from quest.types import (
    QTupleComponent,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QKind,
    QType,
    TYPE_KIND,
    check_kind,
    is_subtype,
    is_type_equal,
)
from quest.common.diagnostics import QuestTypeError
from quest.types.env import (
    Environment,
    TypeSymbol,
    ValueSymbol,
)
from quest.typechecker.elaborate_types import (
    elaborate_kind_binding,
    elaborate_type,
    elaborate_tuple_type_bindings,
    tuple_type_binding_members,
)
from quest.typechecker.typed_ast import (
    TypedExpr,
    TypedLetValue,
    binding_members,
    TypedTuple,
    TypedTypeWitness,
)
from quest.typechecker.checks import (
    check_distinct_names,
)

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


# The phrases a block may hold and a tuple may not, as error messages name them
_PHRASES_NOT_IN_TUPLES: dict[type, str] = {
    ast.ImportPhrase: "an import",
    ast.InterfaceDecl: "an interface declaration",
    ast.ModuleDecl: "a module declaration",
}


class TupleMixin(Checker):
    """Tuples.

    A construct family of the checker (`checker.Checker`): its methods use the
    checker's state and helpers, reach the dispatch (`check_expr`, `synth_expr`)
    through it, and call the families below this one (checker.py) through
    `self`.
    """

    def _synth_tuple_component(self, b: ast.TupleBinding, env: Environment, loop_depth: int) -> TypedExpr:
        """Synthesizes the value of a tuple's value component, without declaring
        its label."""
        if b.type_annot is not None:
            return self.check_expr(b.value, elaborate_type(b.type_annot, env), env, loop_depth)
        return self.synth_expr(b.value, env, loop_depth)

    def _new_tuple_label(self, name: str, type_val: QType, is_var: bool) -> ValueSymbol:
        """Makes the symbol of the label of a tuple's value component."""
        return ValueSymbol(name=name, type_val=type_val, is_var=is_var, function_depth=self.function_depth)

    def _elaborate_tuple_expr(
        self,
        expr: ast.ExprTuple,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedExpr:
        """Elaborates a tuple constructor: tuple ... end.

        Each member of a group is a component of its own, and a manifest kind is
        not a component: it names a kind for the components after it. Components
        are elaborated in order, and each value component's label is declared
        for the ones after it; a simultaneous declaration's labels are declared
        after its last member, and a recursive declaration's members before any
        of their values.

        Against an expected tuple type, the components must match its fields one
        for one: a type formal takes a type witness, which must have the
        formal's bound (with earlier witnesses substituted) and is substituted
        into the later fields; a manifest type binding takes a type binding
        equal to it; and a value field takes a value component of its name (if
        both have one), checked against its type (a var field must be var, with
        exactly its type; a component's type annotation must be a subtype).
        Labels then have the expected fields' names and types, and the tuple has
        the expected type. Against any other type, the tuple is synthesized and
        must be a subtype. Synthesized, its type is made of its components'
        types.
        """
        expected_tuple: Optional[QTupleType] = None
        if expected_type is not None:
            expected_lazy = expected_type.evaluate_lazily(env)
            if not isinstance(expected_lazy, QTupleType):
                return self._check_subsumption(expr, expected_type, env, loop_depth, type_desc="Tuple")
            expected_tuple = expected_lazy
        checking = expected_tuple is not None

        # 1. Flatten the components. A group (let ... and ..., or a group of
        #    type bindings) contributes each of its members, so that fields[i]
        #    lines up with the expected type's i-th field; the maps below
        #    remember the group each member came from, since a group's members
        #    are declared together. Then the count is checked.
        #
        # The components, with the manifest kinds declared just before the
        # component that follows them (kinds_before[i] precedes fields[i]).
        # Against an expected type, the names in groups are checked here, before
        # the arity; synthesized, as each group is reached.
        fields: list[ast.BindingNode] = []
        # The type binding or group each type member comes from, and the
        # recursive (let rec) and simultaneous (let ... and ...) value
        # declarations each value member belongs to, with their members
        type_bindings: dict[int, ast.TypeBinding | ast.TypeBindingGroup] = {}
        rec_members: dict[int, tuple[ast.BindingNode, tuple[ast.LetValueBinding, ...]]] = {}
        simultaneous_members: dict[int, tuple[ast.TupleBinding, ...]] = {}
        kinds_before: dict[int, list[ast.DefKindBinding]] = {}
        for b in expr.fields:
            match b:
                case ast.DefKindBinding():
                    kinds_before.setdefault(len(fields), []).append(b)
                case ast.TypeBinding() | ast.TypeBindingGroup():
                    if checking:
                        members = tuple_type_binding_members(b)
                    else:
                        members = b.bindings if isinstance(b, ast.TypeBindingGroup) else (b,)
                    fields.extend(members)
                    type_bindings.update((id(member), b) for member in members)
                case ast.LetValueBinding() | ast.LetValueBindingGroup():
                    value_members = b.bindings if isinstance(b, ast.LetValueBindingGroup) else (b,)
                    if checking:
                        check_distinct_names(value_members)
                    fields.extend(value_members)
                    rec_members.update((id(member), (b, value_members)) for member in value_members)
                case ast.TupleBindingGroup():
                    if checking:
                        check_distinct_names(b.bindings)
                    fields.extend(b.bindings)
                    simultaneous_members.update((id(member), b.bindings) for member in b.bindings)
                case ast.TupleBinding():
                    fields.append(b)
                case _:
                    # Phrases a tuple cannot hold (imports, modules,
                    # interfaces), rejected before the arity is checked
                    raise TypeError(
                        f"Unsupported tuple component: {_PHRASES_NOT_IN_TUPLES.get(type(b), type(b).__name__)}",
                        offset=b.offset,
                    )
        if expected_tuple is not None and len(fields) != len(expected_tuple.fields):
            raise TypeError(
                f"Tuple arity mismatch: expected {len(expected_tuple.fields)} components, got {len(fields)}",
                offset=expr.offset,
            )

        # 2. Elaborate the components in order, in a scope of their own, so that
        #    each type component and each label (a value component's name) is in
        #    scope for the components after it. Each component falls into one of
        #    four cases, chosen by what the expected type says of it (checking)
        #    or what it is (synthesizing).
        with env.scoped("tuple_check" if checking else "tuple_synth"):
            witness_subst: dict[int, QType] = {}
            elem_typeds: list[TypedExpr] = []
            # The components of a synthesized tuple's type
            q_fields: list[QTupleComponent] = []
            witnesses: dict[int, tuple[TypeSymbol, Optional[QKind]]] = {}
            # The symbols of recursive value members, declared once the first
            # member of their declaration is reached (checking), or their typed
            # declarations, elaborated then (synthesizing)
            rec_symbols: dict[int, ValueSymbol] = {}
            rec_typed: dict[int, TypedLetValue] = {}
            rec_groups: list[tuple[int, ...]] = []
            simultaneous_groups: list[tuple[int, ...]] = []
            # The labels of a simultaneous declaration's members, declared once
            # its last member has been elaborated, as (element index, name,
            # type, is_var, symbol); a synthesized label's symbol is made when
            # it is declared
            pending_labels: list[tuple[int, str, QType, bool, Optional[ValueSymbol]]] = []
            # The symbol of each labeled element's label, by element index
            labels: dict[int, ValueSymbol] = {}
            group_indices: list[int] = []

            def witness_of(binding: ast.TypeBinding) -> tuple[TypeSymbol, Optional[QKind]]:
                """Elaborates a type binding's witness, with its declared bound
                if any; the members of a group are elaborated together, before
                any of them is declared."""
                if id(binding) not in witnesses:
                    for member, symbol, bound in elaborate_tuple_type_bindings(type_bindings[id(binding)], env):
                        witnesses[id(member)] = (symbol, bound)
                return witnesses[id(binding)]

            for index, b in enumerate(fields):
                for kind_binding in kinds_before.get(index, ()):
                    elaborate_kind_binding(kind_binding, env)
                exp_f = expected_tuple.fields[index] if expected_tuple is not None else None

                # A type formal of the expected type, A::K: the component is A's
                # witness, the type hidden behind A. It must have A's bound. A
                # is declared under the formal's own symbol with the witness as
                # its definition, so that the later components see through it,
                # while the tuple's type, the expected one, keeps A abstract;
                # witness_subst carries the witness into the later expected
                # fields.
                if isinstance(exp_f, QTupleTypeFormal):
                    if not isinstance(b, ast.TypeBinding):
                        raise TypeError(
                            f"Expected type witness for type formal '{exp_f.name}', got value component",
                            offset=b.offset,
                        )
                    if b.name != exp_f.name:
                        raise TypeError(
                            f"Tuple type formal name mismatch: expected '{exp_f.name}', got '{b.name}'",
                            offset=b.offset,
                        )
                    witness_type = witness_of(b)[0].definition
                    expected_bound = exp_f.bound.substitute(witness_subst)
                    check_kind(witness_type, expected_bound, env)
                    witness_subst[exp_f.symbol_id] = witness_type
                    env.current_scope.declare_type(
                        TypeSymbol(
                            name=exp_f.name,
                            symbol_id=exp_f.symbol_id,
                            kind=expected_bound,
                            definition=witness_type,
                        )
                    )
                    elem_typeds.append(
                        TypedTypeWitness(
                            name=exp_f.name,
                            witness_type=witness_type,
                            bound=expected_bound,
                            offset=b.offset,
                        )
                    )

                # A type defined by the expected type, A = T: the component must
                # define A as T
                elif isinstance(exp_f, QTupleTypeBinding):
                    if not isinstance(b, ast.TypeBinding):
                        raise TypeError(
                            f"Expected type binding for '{exp_f.name}', got value component",
                            offset=b.offset,
                        )
                    if b.name != exp_f.name:
                        raise TypeError(
                            f"Tuple type binding name mismatch: expected '{exp_f.name}', got '{b.name}'",
                            offset=b.offset,
                        )
                    witness_type = witness_of(b)[0].definition
                    expected_type_val = exp_f.type_val.substitute(witness_subst)
                    if not is_type_equal(witness_type, expected_type_val, env):
                        raise TypeError(
                            f"Type binding '{exp_f.name}' must match manifest type '{expected_type_val}', "
                            f"got '{witness_type}'",
                            offset=b.offset,
                        )
                    env.current_scope.declare_type(
                        TypeSymbol(
                            name=exp_f.name,
                            symbol_id=env.fresh_symbol_id(),
                            kind=exp_f.bound or TYPE_KIND,
                            definition=witness_type,
                        )
                    )
                    elem_typeds.append(
                        TypedTypeWitness(
                            name=exp_f.name,
                            witness_type=witness_type,
                            bound=exp_f.bound,
                            offset=b.offset,
                        )
                    )

                # Synthesizing, a type component: it is declared for the
                # components after it, and is a defined type component of the
                # tuple's type
                elif isinstance(b, ast.TypeBinding):
                    if exp_f is not None:
                        raise TypeError(
                            f"Unexpected type binding '{b.name}' for value field '{exp_f.name}'",
                            offset=b.offset,
                        )
                    symbol, bound = witness_of(b)
                    k_bound = bound or TYPE_KIND
                    env.current_scope.declare_type(symbol)
                    elem_typeds.append(
                        TypedTypeWitness(
                            name=b.name,
                            witness_type=symbol.definition,
                            bound=k_bound,
                            offset=b.offset,
                        )
                    )
                    q_fields.append(QTupleTypeBinding(name=b.name, type_val=symbol.definition, bound=k_bound))

                # A value component. The members of a let rec are all declared
                # when the first is reached, so that each can refer to the
                # others; those of a let ... and ... have their labels declared
                # after the last.
                else:
                    if exp_f is not None:
                        assert isinstance(exp_f, QTupleField)
                        if exp_f.name is not None and b.name is not None and b.name != exp_f.name:
                            raise TypeError(
                                f"Tuple field name mismatch: expected '{exp_f.name}', got '{b.name}'",
                                offset=b.offset,
                            )
                        expected_field_type = exp_f.type_val.substitute(witness_subst)

                    if id(b) in rec_members:
                        binding, group = rec_members[id(b)]
                        if b is group[0]:
                            group_indices = []
                            if exp_f is None:
                                typed_binding = self._elaborate_binding(binding, env, loop_depth)
                                rec_typed.update(zip((id(m) for m in group), binding_members(typed_binding)))
                            else:
                                rec_symbols.update((id(m), self._declare_rec_value(m, env)) for m in group)
                        if exp_f is None:
                            typed_member = rec_typed[id(b)]
                            rec_sym = typed_member.symbol
                            q_fields.append(
                                QTupleField(name=typed_member.name, type_val=rec_sym.type_val, is_var=rec_sym.is_var)
                            )
                        else:
                            rec_sym = rec_symbols[id(b)]
                            if exp_f.is_var:
                                raise TypeError(
                                    f"Tuple field '{exp_f.name or ''}' must be declared mutable (var)",
                                    offset=b.offset,
                                )
                            if not is_subtype(rec_sym.type_val, expected_field_type, env):
                                raise TypeError(
                                    f"Tuple field '{b.name}' declared type '{rec_sym.type_val}' is not a subtype "
                                    f"of expected field type '{expected_field_type}'",
                                    offset=b.offset,
                                )
                            typed_member = self._check_rec_value(b, rec_sym, env, loop_depth)
                        group_indices.append(len(elem_typeds))
                        labels[len(elem_typeds)] = rec_sym
                        elem_typeds.append(typed_member.value)
                        if b is group[-1]:
                            rec_groups.append(tuple(group_indices))
                        continue

                    if not checking and id(b) in simultaneous_members and b is simultaneous_members[id(b)][0]:
                        check_distinct_names(simultaneous_members[id(b)])
                    assert isinstance(b, ast.TupleBinding)
                    if exp_f is None:
                        val_typed = self._synth_tuple_component(b, env, loop_depth)
                        q_fields.append(QTupleField(name=b.name, type_val=val_typed.type_val, is_var=b.is_var))
                        label_name, label_type, label_is_var = b.name, val_typed.type_val, b.is_var
                    else:
                        if exp_f.is_var:
                            if not b.is_var:
                                raise TypeError(
                                    f"Tuple field '{exp_f.name or ''}' must be declared mutable (var)",
                                    offset=b.offset,
                                )
                            val_typed = self.check_expr(b.value, expected_field_type, env, loop_depth)
                            if not is_type_equal(val_typed.type_val, expected_field_type, env):
                                raise TypeError(
                                    f"Mutable tuple field '{exp_f.name or ''}' is invariant; "
                                    f"expected '{expected_field_type}', got '{val_typed.type_val}'",
                                    offset=b.offset,
                                )
                        elif b.type_annot is not None:
                            annot_type = elaborate_type(b.type_annot, env)
                            if not is_subtype(annot_type, expected_field_type, env):
                                raise TypeError(
                                    f"Tuple field '{b.name}' declared type '{annot_type}' is not a subtype "
                                    f"of expected field type '{expected_field_type}'",
                                    offset=b.offset,
                                )
                            val_typed = self.check_expr(b.value, annot_type, env, loop_depth)
                        else:
                            val_typed = self.check_expr(b.value, expected_field_type, env, loop_depth)
                        label_name, label_type, label_is_var = exp_f.name, expected_field_type, exp_f.is_var

                    element_index = len(elem_typeds)
                    elem_typeds.append(val_typed)
                    if id(b) in simultaneous_members:
                        group = simultaneous_members[id(b)]
                        if b is group[0]:
                            group_indices = []
                        group_indices.append(element_index)
                        if label_name is not None:
                            label = self._new_tuple_label(label_name, label_type, label_is_var) if checking else None
                            pending_labels.append((element_index, label_name, label_type, label_is_var, label))
                        if b is group[-1]:
                            simultaneous_groups.append(tuple(group_indices))
                            for pending_index, name, type_val, is_var, pending_label in pending_labels:
                                labels[pending_index] = env.current_scope.declare_value(
                                    pending_label or self._new_tuple_label(name, type_val, is_var)
                                )
                            pending_labels = []
                    elif label_name is not None:
                        labels[element_index] = env.current_scope.declare_value(
                            self._new_tuple_label(label_name, label_type, label_is_var)
                        )

            # Trailing manifest kinds name nothing, but are still checked
            for kind_binding in kinds_before.get(len(fields), ()):
                elaborate_kind_binding(kind_binding, env)

            # 3. Checking, the tuple has the expected type; synthesizing, the
            #    type made of its components' types
            return TypedTuple(
                elements=tuple(elem_typeds),
                type_val=expected_tuple if expected_tuple is not None else QTupleType(tuple(q_fields)),
                rec_groups=tuple(rec_groups),
                simultaneous_groups=tuple(simultaneous_groups),
                labels=tuple(labels.get(i) for i in range(len(elem_typeds))),
                offset=expr.offset,
            )
