"""Elaboration of aggregates: records, tuples (with their type components and labels), member selection, options,
variants and their tag queries and assertions, arrays, and indexing."""

from __future__ import annotations

from typing import Optional

import quest.syntax.ast as ast
from quest.types import (
    BOOL_TYPE,
    binds_module,
    INT_TYPE,
    OK_TYPE,
    QArrayType,
    QOptionType,
    QRecordField,
    QRecordType,
    QTupleComponent,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QPathType,
    type_mentions_symbol_ids,
    QType,
    QVariantType,
    TYPE_KIND,
    check_kind,
    is_subtype,
    is_type_equal,
    resolve_record_bound,
    resolve_variant_bound,
)
from quest.types.env import (
    Environment,
    TypeSymbol,
    ValueSymbol,
)
from quest.diagnostics import QuestTypeError
from quest.typechecker.elaborate_types import (
    elaborate_kind_binding,
    elaborate_type,
    elaborate_tuple_type_bindings,
    tuple_type_binding_members,
)
from quest.typechecker.typed_ast import (
    TypedArray,
    TypedArrayRep,
    TypedExpr,
    TypedIndex,
    TypedIndexAssign,
    binding_members,
    TypedOption,
    TypedRecord,
    TypedRecordField,
    TypedSelect,
    TypedTuple,
    TypedTypeWitness,
    TypedVar,
    TypedVariant,
    TypedVariantAssert,
    TypedVariantCheck,
)
from quest.typechecker.checks import (
    check_distinct_names,
    join_types,
)

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class AggregateMixin:
    """Records, tuples, selection, options, variants, and arrays.

    A mixin of `TypeElaborator` (in `typecheck.py`): its methods use the elaborator's state and its dispatch
    (`check_expr`, `synth_expr`), and call the other families' methods through `self`.
    """

    def _resolve_variant_or_option_field(
        self,
        target_type: QType,
        tag: str,
        op_desc: str,
        offset: int,
        env: Optional[Environment] = None,
    ) -> tuple[Optional[QType], bool]:
        """Resolves payload type and option flag for a tag on Variant or Option target types."""
        if isinstance(target_type, QVariantType):
            field = target_type.get_variant(tag)
            if field is None:
                raise TypeError(
                    f"Tag '{tag}' is not a valid variant of type '{target_type}'",
                    offset=offset,
                )
            return field.type_val, False
        elif isinstance(target_type, QOptionType):
            opt = target_type.get_option(tag)
            if opt is None:
                raise TypeError(
                    f"Tag '{tag}' is not a valid option of type '{target_type}'",
                    offset=offset,
                )
            return opt.payload_type, True
        elif (var_bound := resolve_variant_bound(target_type, env)) is not None:
            field = var_bound.get_variant(tag)
            if field is None:
                raise TypeError(
                    f"Tag '{tag}' is not a valid variant of bound '{var_bound}'",
                    offset=offset,
                )
            return field.type_val, False
        else:
            raise TypeError(
                f"{op_desc} requires Variant or Option target, got '{target_type}'",
                offset=offset,
            )

    def _elaborate_record_expr(
        self,
        expr: ast.ExprRecord,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedExpr:
        """Elaborates a record constructor: record [var] x = e1 ... end.

        Against an expected record type, every expected field must be given, and is checked against its type in the
        expected type's order (a var field must be var, with exactly its type); the fields the expected type does not
        have are then synthesized, and the record has the expected type. Against any other type, the record is
        synthesized and must be a subtype. Synthesized, its fields are synthesized in order.
        """
        expected_rec: Optional[QRecordType] = None
        if expected_type is not None:
            expected_lazy = expected_type.evaluate_lazily(env)
            if not isinstance(expected_lazy, QRecordType):
                return self._check_subsumption(expr, expected_type, env, loop_depth, type_desc="Record")
            expected_rec = expected_lazy

        field_map = {b.name: b for b in expr.fields}
        field_typeds: list[TypedRecordField] = []

        for exp_f in expected_rec.fields if expected_rec is not None else ():
            if exp_f.name not in field_map:
                raise TypeError(
                    f"Record constructor missing required field '{exp_f.name}' of type '{exp_f.type_val}'",
                    offset=expr.offset,
                )
            b = field_map[exp_f.name]
            if exp_f.is_var:
                if not b.is_var:
                    raise TypeError(
                        f"Field '{exp_f.name}' in record must be declared mutable (var)",
                        offset=b.offset,
                    )
                val_typed = self.check_expr(b.value, exp_f.type_val, env, loop_depth)
                if not is_type_equal(val_typed.type_val, exp_f.type_val, env):
                    raise TypeError(
                        f"Mutable record field '{exp_f.name}' is invariant; expected '{exp_f.type_val}', "
                        f"got '{val_typed.type_val}'",
                        offset=b.offset,
                    )
            else:
                val_typed = self.check_expr(b.value, exp_f.type_val, env, loop_depth)

            field_typeds.append(
                TypedRecordField(name=b.name, value=val_typed, is_var=b.is_var, offset=b.offset)
            )

        for b in expr.fields:
            if expected_rec is None or expected_rec.get_field(b.name) is None:
                val_typed = self.synth_expr(b.value, env, loop_depth)
                field_typeds.append(
                    TypedRecordField(name=b.name, value=val_typed, is_var=b.is_var, offset=b.offset)
                )

        if expected_rec is not None:
            rec_type = expected_rec
        else:
            rec_type = QRecordType(
                fields=tuple(
                    QRecordField(name=f.name, type_val=f.value.type_val, is_var=f.is_var) for f in field_typeds
                )
            )
        return TypedRecord(fields=tuple(field_typeds), type_val=rec_type, offset=expr.offset)

    def _synth_tuple_component(self, b: ast.TupleBinding, env: Environment, loop_depth: int) -> TypedExpr:
        """Synthesizes the value of a tuple's value component, without declaring its label."""
        if b.type_annot is not None:
            return self.check_expr(b.value, elaborate_type(b.type_annot, env), env, loop_depth)
        return self.synth_expr(b.value, env, loop_depth)

    def _declare_tuple_label(
        self, name: Optional[str], type_val: QType, is_var: bool, env: Environment
    ) -> Optional[ValueSymbol]:
        """Declares the label of a tuple's value component, for the components after it, returning its symbol."""
        if name is None:
            return None
        return env.current_scope.declare_value(
            ValueSymbol(name=name, type_val=type_val, is_var=is_var, function_depth=self.function_depth)
        )

    def _synth_tuple_expr(self, expr: ast.ExprTuple, env: Environment, loop_depth: int) -> TypedTuple:
        """Synthesizes a tuple constructor: tuple ... end."""
        with env.scoped("tuple_synth"):
            elem_typeds: list[TypedExpr] = []
            q_fields: list[QTupleComponent] = []
            rec_groups: list[tuple[int, ...]] = []
            simultaneous_groups: list[tuple[int, ...]] = []
            labels: dict[int, ValueSymbol] = {}

            for b in expr.fields:
                if isinstance(b, (ast.TypeBinding, ast.TypeBindingGroup)):
                    # The members of a group are elaborated together, then declared together
                    for member, symbol, bound in elaborate_tuple_type_bindings(b, env):
                        k_bound = bound or TYPE_KIND
                        env.current_scope.declare_type(symbol)
                        elem_typeds.append(
                            TypedTypeWitness(
                                name=member.name,
                                witness_type=symbol.definition,
                                bound=k_bound,
                                offset=member.offset,
                            )
                        )
                        q_fields.append(QTupleTypeBinding(name=member.name, type_val=symbol.definition, bound=k_bound))
                elif isinstance(b, ast.TupleBinding):
                    val_typed = self._synth_tuple_component(b, env, loop_depth)
                    elem_typeds.append(val_typed)
                    q_fields.append(QTupleField(name=b.name, type_val=val_typed.type_val, is_var=b.is_var))
                    if (label := self._declare_tuple_label(b.name, val_typed.type_val, b.is_var, env)) is not None:
                        labels[len(elem_typeds) - 1] = label
                elif isinstance(b, ast.TupleBindingGroup):
                    # Simultaneous: every member's value is elaborated before any label is declared
                    check_distinct_names(b.bindings)
                    members = [(m, self._synth_tuple_component(m, env, loop_depth)) for m in b.bindings]
                    first = len(elem_typeds)
                    simultaneous_groups.append(tuple(range(first, first + len(members))))
                    for m, val_typed in members:
                        elem_typeds.append(val_typed)
                        q_fields.append(QTupleField(name=m.name, type_val=val_typed.type_val, is_var=m.is_var))
                    for k, (m, val_typed) in enumerate(members):
                        if (label := self._declare_tuple_label(m.name, val_typed.type_val, m.is_var, env)) is not None:
                            labels[first + k] = label
                elif isinstance(b, (ast.LetValueBinding, ast.LetValueBindingGroup)):
                    # Recursive: let rec, alone or joined by and, declares its members before checking their values
                    typed_binding = self._elaborate_binding(b, env, loop_depth)
                    members = binding_members(typed_binding)
                    rec_groups.append(tuple(range(len(elem_typeds), len(elem_typeds) + len(members))))
                    for member in members:
                        labels[len(elem_typeds)] = member.symbol
                        elem_typeds.append(member.value)
                        q_fields.append(
                            QTupleField(name=member.name, type_val=member.symbol.type_val, is_var=member.symbol.is_var)
                        )
                elif isinstance(b, ast.DefKindBinding):
                    # A manifest kind names a kind for the later components; it is not a component itself
                    elaborate_kind_binding(b, env)
                else:
                    raise TypeError(
                        f"Unsupported tuple component '{b}'",
                        offset=getattr(b, "offset", expr.offset),
                    )

            tuple_type = QTupleType(tuple(q_fields))
            return TypedTuple(
                elements=tuple(elem_typeds),
                type_val=tuple_type,
                rec_groups=tuple(rec_groups),
                simultaneous_groups=tuple(simultaneous_groups),
                labels=tuple(labels.get(i) for i in range(len(elem_typeds))),
                offset=expr.offset,
            )

    def _check_tuple_expr(
        self,
        expr: ast.ExprTuple,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedTuple:
        """Checks a tuple constructor against an expected tuple type."""
        expected_lazy = expected_type.evaluate_lazily(env)
        if not isinstance(expected_lazy, QTupleType):
            return self._check_subsumption(expr, expected_type, env, loop_depth, type_desc="Tuple")

        # Each member of a group is a component of its own. A manifest kind is not a component: it is declared
        # just before the component that follows it (kinds_before[i] precedes fields[i]).
        fields: list[ast.BindingNode] = []
        # The type binding or group each type member comes from, and the members of the recursive (let rec) and
        # simultaneous (let ... and ...) value declarations each value member belongs to
        type_bindings: dict[int, ast.TypeBinding | ast.TypeBindingGroup] = {}
        rec_members: dict[int, tuple[ast.LetValueBinding, ...]] = {}
        simultaneous_members: dict[int, tuple[ast.TupleBinding, ...]] = {}
        kinds_before: dict[int, list[ast.DefKindBinding]] = {}
        for b in expr.fields:
            if isinstance(b, ast.DefKindBinding):
                kinds_before.setdefault(len(fields), []).append(b)
            elif isinstance(b, (ast.TypeBinding, ast.TypeBindingGroup)):
                members = tuple_type_binding_members(b)
                fields.extend(members)
                type_bindings.update((id(member), b) for member in members)
            elif isinstance(b, (ast.LetValueBinding, ast.LetValueBindingGroup)):
                value_members = b.bindings if isinstance(b, ast.LetValueBindingGroup) else (b,)
                check_distinct_names(value_members)
                fields.extend(value_members)
                rec_members.update((id(member), value_members) for member in value_members)
            elif isinstance(b, ast.TupleBindingGroup):
                check_distinct_names(b.bindings)
                fields.extend(b.bindings)
                simultaneous_members.update((id(member), b.bindings) for member in b.bindings)
            else:
                fields.append(b)
        if len(fields) != len(expected_lazy.fields):
            raise TypeError(
                f"Tuple arity mismatch: expected {len(expected_lazy.fields)} components, got {len(fields)}",
                offset=expr.offset,
            )

        with env.scoped("tuple_check"):
            witness_subst: dict[int, QType] = {}
            elem_typeds: list[TypedExpr] = []
            witnesses: dict[int, QType] = {}
            # The symbols of recursive value members, declared once the first member of their declaration is reached
            rec_symbols: dict[int, ValueSymbol] = {}
            rec_groups: list[tuple[int, ...]] = []
            simultaneous_groups: list[tuple[int, ...]] = []
            # The labels of a simultaneous declaration's members, declared once its last member has been checked
            pending_labels: list[ValueSymbol] = []
            # The symbol of each labeled element's label, by element index
            check_labels: dict[int, ValueSymbol] = {}
            group_indices: list[int] = []

            def witness_of(binding: ast.TypeBinding) -> QType:
                """Elaborates a type binding's witness; the members of a group are elaborated together, before any
                of them is declared."""
                if id(binding) not in witnesses:
                    for member, symbol, _ in elaborate_tuple_type_bindings(type_bindings[id(binding)], env):
                        witnesses[id(member)] = symbol.definition
                return witnesses[id(binding)]

            for index, (b, exp_f) in enumerate(zip(fields, expected_lazy.fields)):
                for kind_binding in kinds_before.get(index, ()):
                    elaborate_kind_binding(kind_binding, env)
                match exp_f:
                    case QTupleTypeFormal(name=formal_name, symbol_id=formal_sym_id, bound=formal_bound):
                        if not isinstance(b, ast.TypeBinding):
                            raise TypeError(
                                f"Expected type witness for type formal '{formal_name}', got value component",
                                offset=getattr(b, "offset", expr.offset),
                            )
                        if b.name != formal_name:
                            raise TypeError(
                                f"Tuple type formal name mismatch: expected '{formal_name}', got '{b.name}'",
                                offset=b.offset,
                            )
                        witness_type = witness_of(b)
                        expected_bound = formal_bound.substitute(witness_subst)
                        check_kind(witness_type, expected_bound, env)
                        witness_subst[formal_sym_id] = witness_type
                        env.current_scope.declare_type(
                            TypeSymbol(
                                name=formal_name,
                                symbol_id=formal_sym_id,
                                kind=expected_bound,
                                definition=witness_type,
                            )
                        )
                        elem_typeds.append(
                            TypedTypeWitness(
                                name=formal_name,
                                witness_type=witness_type,
                                bound=expected_bound,
                                offset=b.offset,
                            )
                        )

                    case QTupleTypeBinding(name=bind_name, type_val=bind_type, bound=bind_bound):
                        if not isinstance(b, ast.TypeBinding):
                            raise TypeError(
                                f"Expected type binding for '{bind_name}', got value component",
                                offset=getattr(b, "offset", expr.offset),
                            )
                        if b.name != bind_name:
                            raise TypeError(
                                f"Tuple type binding name mismatch: expected '{bind_name}', got '{b.name}'",
                                offset=b.offset,
                            )
                        witness_type = witness_of(b)
                        expected_type_val = bind_type.substitute(witness_subst)
                        if not is_type_equal(witness_type, expected_type_val, env):
                            raise TypeError(
                                f"Type binding '{bind_name}' must match manifest type '{expected_type_val}', "
                                f"got '{witness_type}'",
                                offset=b.offset,
                            )
                        env.current_scope.declare_type(
                            TypeSymbol(
                                name=bind_name,
                                symbol_id=env.fresh_symbol_id(),
                                kind=bind_bound or TYPE_KIND,
                                definition=witness_type,
                            )
                        )
                        elem_typeds.append(
                            TypedTypeWitness(
                                name=bind_name,
                                witness_type=witness_type,
                                bound=bind_bound,
                                offset=b.offset,
                            )
                        )

                    case QTupleField(name=field_name, type_val=field_type, is_var=exp_is_var):
                        if isinstance(b, ast.TypeBinding):
                            raise TypeError(
                                f"Unexpected type binding '{b.name}' for value field '{field_name}'",
                                offset=b.offset,
                            )
                        if field_name is not None and b.name is not None and b.name != field_name:
                            raise TypeError(
                                f"Tuple field name mismatch: expected '{field_name}', got '{b.name}'",
                                offset=b.offset,
                            )
                        expected_field_type = field_type.substitute(witness_subst)
                        b_is_var = getattr(b, "is_var", False)
                        if id(b) in rec_members:
                            group = rec_members[id(b)]
                            if b is group[0]:
                                rec_symbols.update((id(m), self._declare_rec_value(m, env)) for m in group)
                            rec_sym = rec_symbols[id(b)]
                            if exp_is_var:
                                raise TypeError(
                                    f"Tuple field '{field_name or ''}' must be declared mutable (var)",
                                    offset=b.offset,
                                )
                            if not is_subtype(rec_sym.type_val, expected_field_type, env):
                                raise TypeError(
                                    f"Tuple field '{b.name}' declared type '{rec_sym.type_val}' is not a subtype "
                                    f"of expected field type '{expected_field_type}'",
                                    offset=b.offset,
                                )
                            if b is group[0]:
                                group_indices = []
                            group_indices.append(len(elem_typeds))
                            check_labels[len(elem_typeds)] = rec_sym
                            elem_typeds.append(self._check_rec_value(b, rec_sym, env, loop_depth).value)
                            if b is group[-1]:
                                rec_groups.append(tuple(group_indices))
                            continue
                        if exp_is_var:
                            if not b_is_var:
                                raise TypeError(
                                    f"Tuple field '{field_name or ''}' must be declared mutable (var)",
                                    offset=getattr(b, "offset", expr.offset),
                                )
                            val_typed = self.check_expr(b.value, expected_field_type, env, loop_depth)
                            if not is_type_equal(val_typed.type_val, expected_field_type, env):
                                raise TypeError(
                                    f"Mutable tuple field '{field_name or ''}' is invariant; "
                                    f"expected '{expected_field_type}', got '{val_typed.type_val}'",
                                    offset=getattr(b, "offset", expr.offset),
                                )
                        elif getattr(b, "type_annot", None) is not None:
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
                        label = None
                        if field_name is not None:
                            label = ValueSymbol(
                                name=field_name,
                                type_val=expected_field_type,
                                is_var=exp_is_var,
                                function_depth=self.function_depth,
                            )
                        if id(b) in simultaneous_members:
                            # The labels of a simultaneous declaration are declared after its last member
                            group = simultaneous_members[id(b)]
                            if b is group[0]:
                                group_indices = []
                            group_indices.append(len(elem_typeds))
                            if label is not None:
                                check_labels[len(elem_typeds)] = label
                                pending_labels.append(label)
                            elem_typeds.append(val_typed)
                            if b is group[-1]:
                                simultaneous_groups.append(tuple(group_indices))
                                for pending in pending_labels:
                                    env.current_scope.declare_value(pending)
                                pending_labels = []
                            continue
                        if label is not None:
                            check_labels[len(elem_typeds)] = label
                            env.current_scope.declare_value(label)
                        elem_typeds.append(val_typed)

            # Trailing manifest kinds name nothing, but are still checked
            for kind_binding in kinds_before.get(len(fields), ()):
                elaborate_kind_binding(kind_binding, env)

            return TypedTuple(
                elements=tuple(elem_typeds),
                type_val=expected_lazy,
                rec_groups=tuple(rec_groups),
                simultaneous_groups=tuple(simultaneous_groups),
                labels=tuple(check_labels.get(i) for i in range(len(elem_typeds))),
                offset=expr.offset,
            )

    def _synth_select_expr(self, expr: ast.ExprSelect, env: Environment, loop_depth: int) -> TypedSelect:
        """Synthesizes a field selection on a record, tuple, or module: target.field."""
        if isinstance(expr.target, ast.ExprId):
            module_scope = env.lookup_module(expr.target.name)
            mod_sym = env.lookup_value(expr.target.name)
            # A value binding that shadows the module is selected from as any other value
            if module_scope is not None and (mod_sym is None or binds_module(expr.target.name, mod_sym.type_val)):
                if mod_sym is None:
                    raise TypeError(
                        f"Undefined identifier '{expr.target.name}'",
                        offset=expr.target.offset,
                    )
                val_sym = module_scope.lookup_value_local(expr.field)
                if val_sym is None:
                    raise TypeError(
                        f"Module '{expr.target.name}' has no exported member '{expr.field}'",
                        offset=expr.offset,
                    )
                target_typed = TypedVar(
                    name=expr.target.name,
                    symbol=mod_sym,
                    type_val=mod_sym.type_val,
                    offset=expr.target.offset,
                )
                return TypedSelect(
                    target=target_typed,
                    field=expr.field,
                    type_val=val_sym.type_val,
                    offset=expr.offset,
                )

        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)

        match target_type:
            case QRecordType():
                rec_f = target_type.get_field(expr.field)
                if rec_f is None:
                    raise TypeError(
                        f"Record type '{target_type}' has no field named '{expr.field}'",
                        offset=expr.offset,
                    )
                return TypedSelect(target=target_typed, field=expr.field, type_val=rec_f.type_val, offset=expr.offset)

            case _ if (rec_bound := resolve_record_bound(target_type, env)) is not None:
                rec_f = rec_bound.get_field(expr.field)
                if rec_f is None:
                    raise TypeError(
                        f"Bounded record type '{target_type}' has no field named '{expr.field}'",
                        offset=expr.offset,
                    )
                return TypedSelect(target=target_typed, field=expr.field, type_val=rec_f.type_val, offset=expr.offset)

            case QTupleType():
                tup_f = target_type.get_field(expr.field)
                if tup_f is None:
                    raise TypeError(
                        f"Tuple type '{target_type}' has no field named '{expr.field}'",
                        offset=expr.offset,
                    )
                if isinstance(tup_f, (QTupleTypeFormal, QTupleTypeBinding)):
                    raise TypeError(
                        f"Cannot select type component '{expr.field}' as a value expression",
                        offset=expr.offset,
                    )

                formal_sym_ids = {f.symbol_id for f in target_type.type_formals}
                is_dependent = type_mentions_symbol_ids(tup_f.type_val, formal_sym_ids)

                if is_dependent:
                    if not isinstance(expr.target, ast.ExprId):
                        raise TypeError(
                            f"Cannot select type-dependent member '{expr.field}' from compound or anonymous "
                            f"existential tuple; bind to an immutable variable first",
                            offset=expr.offset,
                        )
                    val_sym = env.lookup_value(expr.target.name)
                    if val_sym is not None and val_sym.is_var:
                        raise TypeError(
                            f"Cannot select type-dependent member '{expr.field}' from mutable variable "
                            f"'{expr.target.name}'; bind to an immutable variable first",
                            offset=expr.offset,
                        )
                    root_sym_id = val_sym.symbol_id if val_sym else 0
                    subst = {
                        f.symbol_id: QPathType(
                            root_name=expr.target.name,
                            root_symbol_id=root_sym_id,
                            field_name=f.name,
                            bound=f.bound,
                        )
                        for f in target_type.type_formals
                    }
                    field_type = tup_f.type_val.substitute(subst)
                else:
                    field_type = tup_f.type_val

                return TypedSelect(
                    target=target_typed,
                    field=expr.field,
                    type_val=field_type,
                    offset=expr.offset,
                )

            case _:
                raise TypeError(
                    f"Cannot select field '{expr.field}' from non-record/tuple type '{target_type}'",
                    offset=expr.offset,
                )

    def _are_option_signatures_compatible(
        self, p1: Optional[QType], p2: Optional[QType], env: Environment
    ) -> bool:
        """Checks if two option branch payload signatures are identical."""
        if p1 is None and p2 is None:
            return True
        if p1 is None or p2 is None:
            return False
        l1 = p1.evaluate_lazily(env)
        l2 = p2.evaluate_lazily(env)
        if isinstance(l1, QTupleType) and isinstance(l2, QTupleType):
            if len(l1.fields) != len(l2.fields):
                return False
            for f1, f2 in zip(l1.fields, l2.fields):
                if f1.name != f2.name:
                    return False
                if not is_type_equal(f1.type_val, f2.type_val, env):
                    return False
            return True
        return is_type_equal(l1, l2, env)

    def _check_option_payload(
        self, payload_expr: ast.Expr, expected_type: QType, env: Environment, loop_depth: int
    ) -> TypedExpr:
        """Checks payload expression against expected branch signature type."""
        expected_lazy = expected_type.evaluate_lazily(env)
        if not isinstance(expected_lazy, QTupleType) and isinstance(payload_expr, ast.ExprTuple):
            if len(payload_expr.fields) == 1 and isinstance(payload_expr.fields[0], ast.TupleBinding):
                return self.check_expr(payload_expr.fields[0].value, expected_lazy, env, loop_depth)
        return self.check_expr(payload_expr, expected_type, env, loop_depth)

    def _synth_option_expr(self, expr: ast.ExprOption, env: Environment, loop_depth: int) -> TypedOption:
        """Synthesizes an option injection: option (tag | ordinal(expr)) [with payload] of OptionType end."""
        opt_type = elaborate_type(expr.option_type, env)
        opt_lazy = opt_type.evaluate_lazily(env)
        if not isinstance(opt_lazy, QOptionType):
            raise TypeError(f"Expected option type in 'of' clause, got '{opt_type}'", offset=expr.offset)

        if expr.ordinal_expr is not None:
            ordinal_typed = self.check_expr(expr.ordinal_expr, INT_TYPE, env, loop_depth)
            if not opt_lazy.options:
                raise TypeError(f"Option type '{opt_type}' has no variants", offset=expr.offset)
            first_payload = opt_lazy.options[0].payload_type
            for branch in opt_lazy.options[1:]:
                if not self._are_option_signatures_compatible(first_payload, branch.payload_type, env):
                    raise TypeError(
                        f"Option construction by ordinal requires all branches to have identical signatures, "
                        f"but variant '{branch.name}' differs from '{opt_lazy.options[0].name}'",
                        offset=expr.offset,
                    )
            if first_payload is not None:
                if expr.payload is None:
                    raise TypeError(
                        f"Option variants require a payload of type '{first_payload}'",
                        offset=expr.offset,
                    )
                payload_typed = self._check_option_payload(expr.payload, first_payload, env, loop_depth)
            else:
                if expr.payload is not None:
                    raise TypeError("Option variants do not accept a payload", offset=expr.offset)
                payload_typed = None
            return TypedOption(
                tag=None,
                type_val=opt_type,
                payload=payload_typed,
                ordinal=0,
                ordinal_expr=ordinal_typed,
                offset=expr.offset,
            )

        assert expr.tag is not None
        opt_field = opt_lazy.get_option(expr.tag)
        if opt_field is None:
            raise TypeError(
                f"Option type '{opt_type}' has no variant tag '{expr.tag}'",
                offset=expr.offset,
            )

        if opt_field.payload_type is not None:
            if expr.payload is None:
                raise TypeError(
                    f"Option variant '{expr.tag}' requires a payload of type '{opt_field.payload_type}'",
                    offset=expr.offset,
                )
            payload_typed = self._check_option_payload(expr.payload, opt_field.payload_type, env, loop_depth)
        else:
            if expr.payload is not None:
                raise TypeError(f"Option variant '{expr.tag}' does not accept a payload", offset=expr.offset)
            payload_typed = None
        ordinal = [f.name for f in opt_lazy.options].index(expr.tag)
        return TypedOption(
            tag=expr.tag,
            type_val=opt_type,
            payload=payload_typed,
            ordinal=ordinal,
            ordinal_expr=None,
            offset=expr.offset,
        )

    def _synth_variant_expr(self, expr: ast.ExprVariant, env: Environment, loop_depth: int) -> TypedVariant:
        """Synthesizes a variant injection: variant tag [with payload] of VariantType end."""
        var_type = elaborate_type(expr.variant_type, env)
        var_lazy = var_type.evaluate_lazily(env)
        if not isinstance(var_lazy, QVariantType):
            raise TypeError(f"Expected variant type in 'of' clause, got '{var_type}'", offset=expr.offset)

        var_field = var_lazy.get_variant(expr.tag)
        if var_field is None:
            raise TypeError(
                f"Variant type '{var_type}' has no tag '{expr.tag}'",
                offset=expr.offset,
            )

        if var_field.type_val is not None:
            if expr.payload is None:
                raise TypeError(
                    f"Variant tag '{expr.tag}' requires a payload of type '{var_field.type_val}'",
                    offset=expr.offset,
                )
            payload_typed = self.check_expr(expr.payload, var_field.type_val, env, loop_depth)
        else:
            if expr.payload is not None:
                raise TypeError(f"Variant tag '{expr.tag}' does not accept a payload", offset=expr.offset)
            payload_typed = None

        return TypedVariant(tag=expr.tag, type_val=var_type, payload=payload_typed, offset=expr.offset)

    def _synth_variant_check_expr(
        self,
        expr: ast.ExprVariantCheck, env: Environment, loop_depth: int
    ) -> TypedVariantCheck:
        """Synthesizes a variant/option tag query: target?tag."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)
        self._resolve_variant_or_option_field(
            target_type, expr.tag, "Variant query '?'", expr.offset, env=env
        )
        return TypedVariantCheck(target=target_typed, tag=expr.tag, type_val=BOOL_TYPE, offset=expr.offset)

    def _synth_variant_assert_expr(
        self,
        expr: ast.ExprVariantAssert, env: Environment, loop_depth: int
    ) -> TypedVariantAssert:
        """Synthesizes a variant/option payload extraction: target!tag."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)
        payload_t, is_option = self._resolve_variant_or_option_field(
            target_type, expr.tag, "Variant assertion '!'", expr.offset, env=env
        )
        if not is_option:
            result_type = payload_t if payload_t is not None else OK_TYPE
        else:
            ordinal_field = QTupleField(name=None, type_val=INT_TYPE)
            if payload_t is None:
                result_type = QTupleType((ordinal_field,))
            else:
                payload_lazy = payload_t.evaluate_lazily(env)
                if isinstance(payload_lazy, QTupleType):
                    result_type = QTupleType((ordinal_field, *payload_lazy.fields))
                else:
                    result_type = QTupleType((ordinal_field, QTupleField(name=None, type_val=payload_lazy)))
        return TypedVariantAssert(target=target_typed, tag=expr.tag, type_val=result_type, offset=expr.offset)

    def _elaborate_array_expr(
        self,
        expr: ast.ExprArray,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedExpr:
        """Elaborates an array literal: array [of :T] e1 e2 ... end.

        The elements are checked against the element type the literal annotates, which must be a subtype of an
        expected array type's, or else against the expected element type; with neither, they are synthesized and
        the element type is the join of theirs. Against a type that is not an array type, the literal is
        synthesized and must be a subtype.
        """
        expected_array: Optional[QArrayType] = None
        if expected_type is not None:
            expected_lazy = expected_type.evaluate_lazily(env)
            if not isinstance(expected_lazy, QArrayType):
                return self._check_subsumption(expr, expected_type, env, loop_depth, type_desc="Array")
            expected_array = expected_lazy

        if getattr(expr, "element_type", None) is not None:
            elem_type: Optional[QType] = elaborate_type(expr.element_type, env)
            if expected_array is not None and not is_subtype(elem_type, expected_array.element_type, env):
                raise TypeError(
                    f"Array element type annotation '{elem_type}' is not a subtype of "
                    f"expected '{expected_array.element_type}'",
                    offset=expr.offset,
                )
        elif expected_array is not None:
            elem_type = expected_array.element_type
        else:
            elem_type = None

        if elem_type is not None:
            elem_typeds = [self.check_expr(e, elem_type, env, loop_depth) for e in expr.elements]
        else:
            if not expr.elements:
                raise TypeError(
                    "Cannot infer element type of empty array; type annotation required",
                    offset=expr.offset,
                )
            elem_typeds = [self.synth_expr(e, env, loop_depth) for e in expr.elements]
            elem_type = join_types(
                [e.type_val for e in elem_typeds],
                env,
                expr.offset,
                error_msg="Incompatible array element types '{t1}' and '{t2}'",
            )

        return TypedArray(
            elements=tuple(elem_typeds),
            type_val=QArrayType(element_type=elem_type),
            offset=expr.offset,
        )

    def _elaborate_array_rep_expr(
        self,
        expr: ast.ExprArrayRep,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedExpr:
        """Elaborates an array repetition: array of (count init) end. Its initial value is checked against an
        expected array type's element type, and the array has the expected type; synthesized, its element type is
        the initial value's. Against a type that is not an array type, it is synthesized and must be a subtype."""
        expected_array: Optional[QArrayType] = None
        if expected_type is not None:
            expected_lazy = expected_type.evaluate_lazily(env)
            if not isinstance(expected_lazy, QArrayType):
                return self._check_subsumption(expr, expected_type, env, loop_depth, type_desc="Array")
            expected_array = expected_lazy

        count_typed = self.check_expr(expr.count, INT_TYPE, env, loop_depth)
        init_typed = self._elaborate_subexpr(
            expr.init_val, expected_array.element_type if expected_array is not None else None, env, loop_depth
        )
        return TypedArrayRep(
            count=count_typed,
            init_val=init_typed,
            type_val=expected_array if expected_array is not None else QArrayType(element_type=init_typed.type_val),
            offset=expr.offset,
        )

    def _synth_index_expr(self, expr: ast.ExprIndex, env: Environment, loop_depth: int) -> TypedIndex:
        """Synthesizes an array indexing expression: arr[i]."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)
        if not isinstance(target_type, QArrayType):
            raise TypeError(f"Cannot index non-array type '{target_type}'", offset=expr.offset)

        idx_typed = self.check_expr(expr.index, INT_TYPE, env, loop_depth)
        return TypedIndex(
            target=target_typed,
            index=idx_typed,
            type_val=target_type.element_type,
            offset=expr.offset,
        )

    def _synth_index_assign_expr(
        self,
        expr: ast.ExprIndexAssign,
        env: Environment,
        loop_depth: int,
    ) -> TypedIndexAssign:
        """Synthesizes an array element assignment: arr[i] := val."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)
        if not isinstance(target_type, QArrayType):
            raise TypeError(
                f"Cannot assign to index of non-array type '{target_type}'",
                offset=expr.offset,
            )

        idx_typed = self.check_expr(expr.index, INT_TYPE, env, loop_depth)
        val_typed = self.check_expr(expr.value, target_type.element_type, env, loop_depth)
        return TypedIndexAssign(
            target=target_typed,
            index=idx_typed,
            value=val_typed,
            type_val=OK_TYPE,
            offset=expr.offset,
        )
