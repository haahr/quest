"""Elaboration of aggregates: records, member selection, options, variants and
their tag queries and assertions, arrays, and indexing. Tuples are
tuples.py's.

The self-hosted counterpart is questlang/typechecker/aggregates."""

from __future__ import annotations

from typing import Optional
import quest.syntax.ast as ast
from quest.typechecker.checker import Checker
from quest.types import (
    BOOL_TYPE,
    binds_module,
    INT_TYPE,
    OK_TYPE,
    QAliasType,
    QArrayType,
    QOptionType,
    QRecordField,
    QRecordType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QPathType,
    type_mentions_symbol_ids,
    QType,
    QVariantType,
    map_aliases,
    is_subtype,
    is_type_equal,
    resolve_record_bound,
    resolve_sum_bound,
    resolve_tuple_bound,
)
from quest.types.env import (
    Environment,
)
from quest.diagnostics import QuestTypeError
from quest.typechecker.elaborate_types import (
    elaborate_type,
)
from quest.typechecker.typed_ast import (
    TypedArray,
    TypedArrayRep,
    TypedExpr,
    TypedIndex,
    TypedIndexAssign,
    TypedOption,
    TypedRecord,
    TypedRecordField,
    TypedSelect,
    TypedVar,
    TypedVariant,
    TypedVariantAssert,
    TypedVariantCheck,
)
from quest.typechecker.checks import (
    join_types,
)
# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class AggregateMixin(Checker):
    """Records, selection, options, variants, and arrays.

    A construct family of the checker (`checker.Checker`): its methods use the
    checker's state and helpers, reach the dispatch (`check_expr`, `synth_expr`)
    through it, and call the families below this one (checker.py) through
    `self`.
    """

    def _resolve_variant_or_option_field(
        self,
        target_type: QType,
        tag: str,
        op_desc: str,
        offset: int,
        env: Optional[Environment] = None,
    ) -> tuple[Optional[QType], bool]:
        """Resolves payload type and option flag for a tag on Variant or Option
        target types."""
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
        elif isinstance(var_bound := resolve_sum_bound(target_type, env), QVariantType):
            field = var_bound.get_variant(tag)
            if field is None:
                raise TypeError(
                    f"Tag '{tag}' is not a valid variant of bound '{var_bound}'",
                    offset=offset,
                )
            return field.type_val, False
        elif isinstance(var_bound, QOptionType):
            opt = var_bound.get_option(tag)
            if opt is None:
                raise TypeError(
                    f"Tag '{tag}' is not a valid option of bound '{var_bound}'",
                    offset=offset,
                )
            return opt.payload_type, True
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

        Against an expected record type, every expected field must be given, and
        is checked against its type in the expected type's order (a var field
        must be var, with exactly its type); the fields the expected type does
        not have are then synthesized, and the record has the expected type.
        Against any other type, the record is synthesized and must be a subtype.
        Synthesized, its fields are synthesized in order.
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

    def _synth_select_expr(self, expr: ast.ExprSelect, env: Environment, loop_depth: int) -> TypedSelect:
        """Synthesizes a selection target.field from a module, a record, or a
        tuple.

        m.f, where m names an imported module that no value shadows, has the
        type the module gives f. A record's field has the type it was declared
        with. A tuple's field is the interesting case, because its type may
        mention the tuple's own type components: in a value t of type Tuple
        A::TYPE f: A end, the field f has type A, a name that means nothing
        outside the tuple. When t is a variable, t.f has the path type t.A
        instead (see elaborate_type), which names "t's A" without revealing what
        it is. Such a field can be selected only from an immutable variable: an
        arbitrary expression has no name to root a path type at, and a mutable
        variable's components could change. A component the tuple's type defines
        (A = Int) is known, and is replaced by its definition (_outside_tuple).
        A value whose type is a type parameter bounded by a record or tuple type
        is selected from as a value of its bound.

        A path type must not outlive its root: a block, function, or case branch
        whose type mentions a path type rooted at one of its own variables is
        rejected (check_no_escaping_path_types).
        """
        if isinstance(expr.target, ast.ExprId):
            module_scope = env.lookup_module(expr.target.name)
            mod_sym = env.lookup_value(expr.target.name)
            # A value binding that shadows the module is selected from as any
            # other value
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

        if not isinstance(target_type, (QRecordType, QTupleType)) and resolve_record_bound(target_type, env) is None:
            # A type parameter bounded by a tuple type: selected from as from
            # its bound
            target_type = resolve_tuple_bound(target_type, env) or target_type
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
                field_type = self._outside_tuple(field_type, target_type)

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

    def _outside_tuple(self, t: QType, tuple_type: QTupleType) -> QType:
        """The type t of a field selected from a value of tuple_type, as seen
        outside the tuple, where the names of the tuple's type definitions mean
        nothing: with the definitions in their place. (Naming them through the
        variable the tuple was selected from, as `lists.L`, would print types
        that outlive the variable's scope.)
        """
        definitions = {(c.name, c.type_val) for c in tuple_type.fields if isinstance(c, QTupleTypeBinding)}
        if not definitions:
            return t

        def replace(alias: QAliasType) -> Optional[QType]:
            if (alias.name, alias.target) not in definitions:
                return None
            return map_aliases(alias.target, replace)

        return map_aliases(t, replace)

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
        """Synthesizes an option injection: option (tag | ordinal(expr)) [with
        payload] of OptionType end."""
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
        return TypedOption(
            tag=expr.tag,
            type_val=opt_type,
            payload=payload_typed,
            ordinal_expr=None,
            offset=expr.offset,
        )

    def _synth_variant_expr(self, expr: ast.ExprVariant, env: Environment, loop_depth: int) -> TypedVariant:
        """Synthesizes a variant injection: variant tag [with payload] of
        VariantType end."""
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

        The elements are checked against the element type the literal annotates,
        which must be a subtype of an expected array type's, or else against the
        expected element type; with neither, they are synthesized and the
        element type is the join of theirs. Against a type that is not an array
        type, the literal is synthesized and must be a subtype.
        """
        expected_array: Optional[QArrayType] = None
        if expected_type is not None:
            expected_lazy = expected_type.evaluate_lazily(env)
            if not isinstance(expected_lazy, QArrayType):
                return self._check_subsumption(expr, expected_type, env, loop_depth, type_desc="Array")
            expected_array = expected_lazy

        if expr.element_type is not None:
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
        """Elaborates an array repetition: array of (count init) end. Its
        initial value is checked against an expected array type's element type,
        and the array has the expected type; synthesized, its element type is
        the initial value's. Against a type that is not an array type, it is
        synthesized and must be a subtype."""
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
