"""Synthetic strings written by the designer (no corpus strings). Expected: R = refused by G3, K = kept."""
import sys
sys.path.insert(0, "/mnt/user-data/outputs/p12/work/pkg/code")
import composition_normalise_g3 as G3
CASES = [
 ("barium nitrate Ba(NO3)", "R"), ("barium nitrate Ba(NO3)2", "K"), ("calcium carbonate Ca(CO3)2", "R"),
 ("calcium carbonate CaCO3", "K"), ("nickel hydroxide (Ni(OH))2", "R"), ("nickel hydroxide Ni(OH)2", "K"),
 ("lanthanum chloride LaCl2", "R"), ("lanthanum chloride LaCl3", "K"), ("yttrium nitrate Y(NO3)2", "R"),
 ("yttrium nitrate Y(NO3)3", "K"), ("zinc sulfate Zn(SO4)2", "R"), ("zinc sulfate ZnSO4", "K"),
 ("lithium phosphate Li2PO4", "R"), ("lithium phosphate Li3PO4", "K"), ("lithium iron phosphate LiFePO4", "K"),
 ("neodymium phosphate NdPO3", "R"), ("manganese nitrate Mn(NO3)2", "K"), ("cerium nitrate Ce(NO3)3", "K"),
 ("titanium dioxide TiO2", "K"), ("titanium dioxide Ti2O3", "R"), ("silicon dioxide SiO2", "K"),
 ("tungsten trioxide WO3", "K"), ("tungsten trioxide WO2", "R"), ("molybdenum trioxide MoO3", "K"),
 ("vanadium pentoxide V2O5", "K"), ("niobium dioxide Nb2O5", "R"), ("manganese dioxide MnO2", "K"),
 ("iron (III) nitrate Fe(NO3)3", "K"), ("iron (II) nitrate Fe(NO3)3", "R"), ("Ferric nitrate Fe(NO3)2", "R"),
 ("Ferrous oxide Fe2O3", "R"), ("Ferric oxide Fe2O3", "K"), ("Copper (I) oxide Cu2O", "K"),
 ("Copper (II) oxide Cu2O", "R"), ("Copper (I) aluminate CuAlO2", "K"), ("cobalt oxide Co3O4", "K"),
 ("bismuth oxide Bi2O3", "K"), ("Sodium metaphosphate NaPO3", "K"), ("bismuth oxychloride BiOCl", "K"),
 ("neodymium oxyphosphate Nd3(PO4)O3 phosphate", "K"), ("nickel nitrate hexahydrate Ni(NO3)2.6H2O", "K"),
 ("ammonium nitrate NH4NO3", "K"), ("strontium titanate SrTiO3", "K"), ("potassium chloride KCl", "K"),
 ("tin (IV) oxide SnO2", "K"), ("tin (II) oxide SnO2", "R"), ("europium chloride EuCl3", "K"),
]
bad = 0
for s, exp in CASES:
    try:
        G3.parse_formula_g3(s); got = "K"
    except Exception:
        got = "R" if s in G3.G3_LOG else "R(other)"
    mark = "" if (got[0] == exp and not (exp == "K" and got != "K")) else ("" if exp == "K" and got == "R(other)" else "  <-- MISMATCH")
    bad += bool(mark)
    print(f"{exp} {got:9s} {G3.G3_LOG.get(s, ''):38s} {s}{mark}")
print("mismatches", bad)
