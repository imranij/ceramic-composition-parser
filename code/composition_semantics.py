"""Unit semantics for host + additive compositions (package v0.2.0).

Every percentage convention used here is named and must be declared by the
caller. Nothing is defaulted, because the literature uses more than one basis for
the same unit symbol, and a wrong guess changes the composition silently.

Conventions (p_i is the stated percentage of additive i divided by 100; the host
is H; a is atoms per formula unit, M molar mass, nu_i the amount of the dopant
element in one formula unit of additive i). Each function returns additive-to-host
formula-unit ratios r_i = n_i / n_H, so the host coefficient is always 1.

mol%  basis="total_mixture"  n_i / (n_H + sum_j n_j) = p_i   ->  r_i = p_i / (1 - sum p)
      basis="per_host"       n_i / n_H = p_i                 ->  r_i = p_i
wt%   basis="total_mixture"  m_i / m_total = p_i             ->  r_i = (p_i / M_i) / ((1 - sum p) / M_H)
      basis="per_host"       m_i / m_H = p_i                 ->  r_i = p_i M_H / M_i
at%   counts="additive_phase_atoms" (all atoms of the additive formula unit)
      basis="total_mixture"  a_i n_i / N_atoms = p_i         ->  r_i = p_i a_H / ((1 - sum p) a_i)
      basis="per_host"       a_i n_i / (a_H n_H) = p_i       ->  r_i = p_i a_H / a_i
at%   counts="dopant_element_atoms" (only atoms of the named dopant element)
      basis="total_mixture"  nu_i n_i / N_atoms = p_i        ->  r_i = p_i T / nu_i,
                             T = a_H / (1 - sum_j a_j p_j / nu_j)
      basis="per_host"       nu_i n_i / (a_H n_H) = p_i      ->  r_i = p_i a_H / nu_i
      The dopant element must not occur in the host or in another additive;
      otherwise the count is not defined and the conversion is refused.

Roles are never inferred from the expression. The caller states which component
is the host and which are additives; see ``composition_record`` for records.
"""

from __future__ import annotations

from dataclasses import dataclass

from composition_parser import CompositionRefusal, atomic_fractions, parse_formula

UNITS = ("mol%", "wt%", "at%")
BASES = ("total_mixture", "per_host")
AT_COUNTS = ("additive_phase_atoms", "dopant_element_atoms")


@dataclass(frozen=True)
class MixtureComponent:
    role: str
    formula: str
    coefficient: float           # formula units per formula unit of host


@dataclass(frozen=True)
class Additive:
    formula: str
    percent: float
    dopant_element: str | None = None   # required only for at% dopant_element_atoms


def formula_mass(amounts: dict[str, float]) -> float:
    from pymatgen.core import Element  # pinned dependency; atomic masses per IUPAC

    return sum(float(Element(el).atomic_mass) * a for el, a in amounts.items())


def _fractions(additives: list[Additive]) -> list[float]:
    ps = []
    for a in additives:
        if not (0 < a.percent < 100):
            raise CompositionRefusal(["unit_convention_missing"],
                                     f"percentage must lie in (0, 100): {a}")
        ps.append(a.percent / 100.0)
    if sum(ps) >= 1:
        raise CompositionRefusal(["unit_convention_missing"], "additive percentages sum to >= 100")
    return ps


def additive_ratios(host: str, additives: list[Additive], unit: str, basis: str,
                    at_counts: str | None = None) -> list[float]:
    """Additive-to-host formula-unit ratios r_i under the declared convention."""
    if unit not in UNITS or basis not in BASES:
        raise CompositionRefusal(["unit_convention_missing"], f"unit={unit!r} basis={basis!r}")
    ps = _fractions(additives)
    rest = 1.0 - sum(ps)
    host_amt = parse_formula(host)
    add_amts = [parse_formula(a.formula) for a in additives]
    if unit == "mol%":
        return [p / rest if basis == "total_mixture" else p for p in ps]
    if unit == "wt%":
        mh = formula_mass(host_amt)
        ms = [formula_mass(x) for x in add_amts]
        if basis == "total_mixture":
            return [(p / m) / (rest / mh) for p, m in zip(ps, ms)]
        return [p * mh / m for p, m in zip(ps, ms)]
    # at%
    a_h = sum(host_amt.values())
    a_s = [sum(x.values()) for x in add_amts]
    if at_counts == "additive_phase_atoms":
        if basis == "total_mixture":
            return [p * a_h / (rest * a) for p, a in zip(ps, a_s)]
        return [p * a_h / a for p, a in zip(ps, a_s)]
    if at_counts == "dopant_element_atoms":
        nus = []
        for k, (add, amt) in enumerate(zip(additives, add_amts)):
            e = add.dopant_element
            others = [host_amt] + [x for j, x in enumerate(add_amts) if j != k]
            if not e or e not in amt or any(e in o for o in others):
                raise CompositionRefusal(
                    ["unit_convention_missing"],
                    f"dopant element {e!r} must occur only in additive {add.formula}")
            nus.append(amt[e])
        if basis == "per_host":
            return [p * a_h / nu for p, nu in zip(ps, nus)]
        denom = 1.0 - sum(a * p / nu for a, p, nu in zip(a_s, ps, nus))
        if denom <= 0:
            raise CompositionRefusal(["unit_convention_missing"], "at% exceeds what the additive can supply")
        total_atoms = a_h / denom
        return [p * total_atoms / nu for p, nu in zip(ps, nus)]
    raise CompositionRefusal(["unit_convention_missing"], f"at% requires counts in {AT_COUNTS}")


def percentage_mixture(host: str, additives: list[Additive], unit: str, basis: str,
                       at_counts: str | None = None) -> list[MixtureComponent]:
    ratios = additive_ratios(host, additives, unit, basis, at_counts)
    return [MixtureComponent("host", host, 1.0)] + [
        MixtureComponent("additive", a.formula, r) for a, r in zip(additives, ratios)]


def mixture_amounts(components: list[MixtureComponent]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for component in components:
        if component.coefficient <= 0:
            raise CompositionRefusal(["nonpositive_amount"], f"coefficient of {component.formula}")
        for element, amount in parse_formula(component.formula).items():
            totals[element] = totals.get(element, 0.0) + component.coefficient * amount
    return totals


def mixture_atomic_fractions(components: list[MixtureComponent]) -> dict[str, float]:
    return atomic_fractions(mixture_amounts(components))


# -- binary helpers with the v0.1 names; the basis (and for at% the count) is now required --
def mol_percent_mixture(host_formula: str, additive_formula: str, mol_percent: float, *,
                        basis: str) -> list[MixtureComponent]:
    return percentage_mixture(host_formula, [Additive(additive_formula, mol_percent)], "mol%", basis)


def weight_percent_mixture(host_formula: str, additive_formula: str, weight_percent: float, *,
                           basis: str) -> list[MixtureComponent]:
    return percentage_mixture(host_formula, [Additive(additive_formula, weight_percent)], "wt%", basis)


def atomic_percent_mixture(host_formula: str, additive_formula: str, atomic_percent: float, *,
                           basis: str, at_counts: str,
                           dopant_element: str | None = None) -> list[MixtureComponent]:
    return percentage_mixture(host_formula, [Additive(additive_formula, atomic_percent, dopant_element)],
                              "at%", basis, at_counts)
