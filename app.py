import math
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="DEFLIFE", page_icon="⚙️", layout="wide"
)

# ---------------------------------------------------------
# DATA & CONSTANTS
# ---------------------------------------------------------
METALS = {
    "iron": {
        "name": "Iron",
        "rho": 7850,
        "L": 272000,
        "cm": 835,
        "tf": 1540,
        "src": "ρ, L, θf: Ghosh & Mallik Ex. 2.5; cm: web",
    },
    "aluminium": {
        "name": "Aluminium",
        "rho": 2700,
        "L": 397000,
        "cm": 1090,
        "tf": 660.3,
        "src": "web values",
    },
    "copper": {
        "name": "Copper",
        "rho": 8960,
        "L": 209000,
        "cm": 545,
        "tf": 1084.6,
        "src": "web values; L = 13.26 kJ/mol ÷ 63.546 g/mol",
    },
}

BOOK_SAND = {"k": 0.8655, "rho": 1600, "c": 1170, "t0": 28}

FATIGUE = {
    "iron": {
        "kind": "curve",
        "name": "ASTM A48 Class 30 gray cast iron",
        "uts": 308,
        "stress": [245, 105, 53],
        "cycles": [1e3, 1e5, 2.1e6],
        "tail": " The data stop here, so the real life is not known.",
        "caveat": (
            "Specimen test data with large scatter, used here as a fully"
            " reversed S-N curve (assumption). The casting section uses iron"
            " data from the textbook example."
        ),
    },
    "aluminium": {
        "kind": "curve",
        "name": "A356-T6 cast aluminium",
        "uts": 262,
        "stress": [252, 150, 107, 74.5, 68.9, 68.9],
        "cycles": [500, 5e4, 5e5, 5e6, 5e7, 1e8],
        "tail": (
            " This is on the fatigue plateau of the data, so it is treated as"
            " run-out."
        ),
        "caveat": (
            "Fitted strain-life data from the SAE A356-T6 round-robin study"
            " (reversals divided by 2), used as a stress-amplitude curve. The"
            " casting section uses pure aluminium thermal data, while the"
            " fatigue data are for the A356-T6 alloy."
        ),
    },
    "copper": {
        "kind": "point",
        "name": "C83600 sand-cast bronze",
        "uts": 255,
        "fs": 76,
        "fcyc": 1e8,
        "caveat": (
            "Single reference fatigue strength, not a full curve, so no life"
            " estimate is given. The casting section uses pure copper thermal"
            " data, while the fatigue data are for a bronze alloy."
        ),
    },
}

# ---------------------------------------------------------
# UI SIDEBAR (INPUTS)
# ---------------------------------------------------------
st.sidebar.title("DEFLIFE Parameters")

st.sidebar.header("1. Metal and Pouring")
mat_key = st.sidebar.selectbox(
    "Metal",
    options=["iron", "aluminium", "copper"],
    format_func=lambda x: METALS[x]["name"],
)
sup = st.sidebar.number_input(
    "Superheat [°C]", min_value=0.0, max_value=300.0, value=50.0, step=1.0
)

st.sidebar.header("2. Mould (Sand)")
sand_type = st.sidebar.selectbox(
    "Sand",
    options=["book", "custom"],
    format_func=lambda x: (
        "Sand from Ghosh & Mallik Example 2.5"
        if x == "book"
        else "Custom sand"
    ),
)
if sand_type == "custom":
    sk = st.sidebar.number_input(
        "Conductivity k [W/m·K]",
        min_value=0.2,
        max_value=3.0,
        value=0.8655,
        step=0.01,
    )
    sr = st.sidebar.number_input(
        "Density [kg/m³]",
        min_value=1000.0,
        max_value=2200.0,
        value=1600.0,
        step=10.0,
    )
    sc = st.sidebar.number_input(
        "Specific heat [J/kg·K]",
        min_value=600.0,
        max_value=1500.0,
        value=1170.0,
        step=10.0,
    )
    mo = {"k": sk, "rho": sr, "c": sc, "t0": 28}
else:
    mo = BOOK_SAND

st.sidebar.header("3. Pattern (Casting Size)")
shape = st.sidebar.selectbox(
    "Shape", options=["box", "cylinder", "sphere"], index=0
)
if shape == "box":
    boxL = st.sidebar.number_input(
        "Length [m]", min_value=0.01, max_value=1.0, value=0.10, step=0.01
    )
    boxW = st.sidebar.number_input(
        "Width [m]", min_value=0.01, max_value=1.0, value=0.05, step=0.01
    )
    boxH = st.sidebar.number_input(
        "Height [m]", min_value=0.005, max_value=1.0, value=0.02, step=0.005
    )
elif shape == "cylinder":
    cylR = st.sidebar.number_input(
        "Radius [m]", min_value=0.005, max_value=0.5, value=0.03, step=0.005
    )
    cylH = st.sidebar.number_input(
        "Height [m]", min_value=0.01, max_value=1.0, value=0.10, step=0.01
    )
else:
    sphR = st.sidebar.number_input(
        "Radius [m]", min_value=0.005, max_value=0.5, value=0.05, step=0.005
    )

st.sidebar.header("4. Feeding (Riser and Neck)")
rD = st.sidebar.number_input(
    "Riser diameter [m]",
    min_value=0.005,
    max_value=0.5,
    value=0.04,
    step=0.005,
)
rH = st.sidebar.number_input(
    "Riser height [m]", min_value=0.005, max_value=1.0, value=0.06, step=0.005
)
neck = st.sidebar.number_input(
    "Neck thickness [m]",
    min_value=0.002,
    max_value=0.5,
    value=0.02,
    step=0.002,
)

st.sidebar.header("5. Gating (Sprue)")
sD1 = st.sidebar.number_input(
    "Sprue top diameter [m]",
    min_value=0.005,
    max_value=0.2,
    value=0.03,
    step=0.005,
)
sD2 = st.sidebar.number_input(
    "Sprue bottom diameter [m]",
    min_value=0.003,
    max_value=0.2,
    value=0.015,
    step=0.001,
)
sH = st.sidebar.number_input(
    "Sprue height [m]", min_value=0.05, max_value=1.0, value=0.20, step=0.01
)
basin = st.sidebar.number_input(
    "Metal depth in basin [m]",
    min_value=0.01,
    max_value=0.5,
    value=0.05,
    step=0.01,
)

st.sidebar.header("6. Service Loading (Fatigue)")
smax = st.sidebar.number_input(
    "Maximum service stress [MPa]",
    min_value=1.0,
    max_value=1000.0,
    value=150.0,
    step=5.0,
)
smin = st.sidebar.number_input(
    "Minimum service stress [MPa]",
    min_value=-1000.0,
    max_value=1000.0,
    value=10.0,
    step=5.0,
)
cpd = st.sidebar.number_input(
    "Operating cycles per day",
    min_value=1,
    max_value=10000000,
    value=1000,
    step=100,
)

# ---------------------------------------------------------
# CALCULATIONS
# ---------------------------------------------------------
st.title("DEFLIFE: Casting Defect and Fatigue Life Analysis Tool")
st.caption("Casting analysis, defect flags and fatigue life")

if smax <= smin:
    st.error(
        "Validation Error: Maximum stress must be strictly greater than"
        " minimum stress."
    )
    st.stop()

m = METALS[mat_key]

# 1. Pattern Geometry
if shape == "box":
    vol = boxL * boxW * boxH
    area = 2 * (boxL * boxW + boxL * boxH + boxW * boxH)
    kind = "plane"
elif shape == "cylinder":
    vol = math.pi * cylR * cylR * cylH
    area = 2 * math.pi * cylR * cylR + 2 * math.pi * cylR * cylH
    kind = "cylinder"
else:
    vol = (4.0 / 3.0) * math.pi * (sphR**3)
    area = 4 * math.pi * sphR * sphR
    kind = "sphere"

modulus = vol / area

# 2. Riser Geometry
rVol = (math.pi / 4.0) * rD * rD * rH
rArea = math.pi * rD * rH + (math.pi / 4.0) * rD * rD

# 3. Solidification Times (Ghosh & Mallik eqs 2.35 - 2.39)
cases = [
    {"kind": kind, "va": modulus, "m": m, "mo": mo, "sh": sup},
    {"kind": "cylinder", "va": rVol / rArea, "m": m, "mo": mo, "sh": sup},
    {"kind": "plane", "va": neck / 2.0, "m": m, "mo": mo, "sh": sup},
]

ts = []
for c in cases:
    alpha = c["mo"]["k"] / (c["mo"]["rho"] * c["mo"]["c"])
    Lp = c["m"]["L"] + c["m"]["cm"] * c["sh"]
    lam = (c["m"]["tf"] - c["mo"]["t0"]) * c["mo"]["rho"] * c["mo"]["c"] / (c["m"]["rho"] * Lp)
    b0 = 2.0 * lam / math.sqrt(math.pi)

    if c["kind"] == "plane":
        beta = b0
    elif c["kind"] == "cylinder":
        beta = (b0 + math.sqrt(b0 * b0 + lam)) / 2.0
    else:  # sphere
        beta = (b0 + math.sqrt(b0 * b0 + 4.0 * lam / 3.0)) / 2.0

    ts.append((c["va"] ** 2) / (alpha * (beta**2)))

tCast, tRiser, tNeck = ts[0], ts[1], ts[2]

# 4. Masses, Yield, Heat
mass = vol * m["rho"]
rMass = rVol * m["rho"]
sVol = (math.pi * sH / 12.0) * (sD1**2 + sD1 * sD2 + sD2**2)
pour = mass + rMass + (sVol * m["rho"])
yieldPct = (mass / pour) * 100.0
heat = m["rho"] * vol * (m["L"] + m["cm"] * sup) / 1000.0

# 5. Filling and Sprue
gArea = (math.pi / 4.0) * sD2 * sD2
a1 = (math.pi / 4.0) * sD1 * sD1
vel = math.sqrt(2.0 * 9.81 * (sH + basin))
tFill = (vol + rVol) / (gArea * vel)
aIdeal = a1 * math.sqrt(basin / (basin + sH))

# 6. Defect Flags
f1 = tRiser <= tCast
f2 = tFill > tCast
f3 = tNeck < tCast
f4 = gArea > aIdeal

# ---------------------------------------------------------
# DISPLAY RESULTS
# ---------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Casting Parameters")
    st.write(
        f"**Volume:** {vol * 1e6:.1f} cm³  \n**Surface Area:** {area * 1e4:.1f}"
        f" cm²  \n**Mass:** {mass:.3f} kg  \n**Modulus V/A:**"
        f" {modulus * 1000:.2f} mm"
    )

    st.subheader("Solidification")
    st.write(
        f"**Casting time:** {tCast:.1f} s  \n**Riser time:** {tRiser:.1f} s "
        f" \n**Neck time:** {tNeck:.1f} s  \n**Riser ÷ casting time:**"
        f" {tRiser / tCast:.2f}"
    )

with c2:
    st.subheader("Filling")
    st.write(
        f"**Fill velocity:** {vel:.2f} m/s  \n**Fill time (casting +"
        f" riser):** {tFill:.2f} s  \n**Sprue bottom area:** {gArea * 1e4:.2f}"
        f" cm²  \n**Ideal sprue bottom area:** {aIdeal * 1e4:.2f} cm²"
    )

    st.subheader("Metal & Heat")
    st.write(
        f"**Pouring temp:** {m['tf'] + sup:.0f} °C  \n**Pouring weight:**"
        f" {pour:.3f} kg  \n**Yield:** {yieldPct:.1f} %  \n**Heat to remove:**"
        f" {heat:.0f} kJ"
    )

st.markdown("---")
st.subheader("Defect Flags")

flags = [
    (
        "Shrinkage",
        f1,
        (
            f"riser time ({tRiser:.1f} s) must exceed casting time ({tCast:.1f}"
            " s)"
        ),
    ),
    (
        "Misrun / cold shut",
        f2,
        f"fill time ({tFill:.2f} s) must be below casting time ({tCast:.1f} s)",
    ),
    (
        "Hot spot",
        f3,
        (
            f"neck time ({tNeck:.1f} s) must not be below casting time"
            f" ({tCast:.1f} s)"
        ),
    ),
    (
        "Gas porosity",
        f4,
        (
            f"sprue bottom ({gArea * 1e4:.2f} cm²) must not exceed ideal"
            f" ({aIdeal * 1e4:.2f} cm²)"
        ),
    ),
]

for name, is_risk, reason in flags:
    if is_risk:
        st.error(f"❌ **{name}**: **RISK** — {reason}")
    else:
        st.success(f"✅ **{name}**: **No risk** — {reason}")

# ---------------------------------------------------------
# FATIGUE LIFE ANALYSIS
# ---------------------------------------------------------
st.markdown("---")
st.subheader("Fatigue Life Analysis")

fd = FATIGUE[mat_key]
sa = (smax - smin) / 2.0
sm = (smax + smin) / 2.0
sm_eff = max(0.0, sm)

st.write(f"**Fatigue Data used:** {fd['name']}")
st.write(f"**Alternating stress σa:** {sa:.1f} MPa")
st.write(f"**Mean stress σm:** {sm:.1f} MPa")

fNote = ""
have_life = False
lifeN = 0.0

if smax >= fd["uts"]:
    fNote = (
        f"Maximum stress is at or above the tensile strength ({fd['uts']} MPa):"
        " the part is expected to fail on the first load."
    )
else:
    sar = sa / (1.0 - (sm_eff / fd["uts"]))
    st.write(f"**Goodman-corrected stress σar:** {sar:.1f} MPa")

    if fd["kind"] == "curve":
        nn = len(fd["stress"])
        if sar > fd["stress"][0]:
            fNote = (
                "Equivalent stress is above the highest stress in the data"
                f" ({fd['stress'][0]} MPa): the life is shorter than"
                f" {fd['cycles'][0]:.1e} cycles, outside the data range."
            )
        elif sar <= fd["stress"][-1]:
            yrs_val = fd["cycles"][-1] / (365.0 * cpd)
            fNote = (
                "Equivalent stress is at or below the lowest stress in the data"
                f" ({fd['stress'][-1]} MPa): the life is beyond"
                f" {fd['cycles'][-1]:.1e} cycles (more than {yrs_val:.1f}"
                f" years).{fd['tail']}"
            )
        else:
            for j in range(nn - 1):
                if fd["stress"][j] >= sar > fd["stress"][j + 1]:
                    log_s1, log_s2 = math.log10(fd["stress"][j]), math.log10(
                        fd["stress"][j + 1]
                    )
                    log_c1, log_c2 = math.log10(fd["cycles"][j]), math.log10(
                        fd["cycles"][j + 1]
                    )
                    lN = log_c1 + (math.log10(sar) - log_s1) / (
                        log_s2 - log_s1
                    ) * (log_c2 - log_c1)
                    lifeN = 10**lN
                    have_life = True
                    break
    elif sar <= fd["fs"]:
        fNote = (
            f"Equivalent stress is below reference fatigue strength ({fd['fs']}"
            f" MPa at {fd['fcyc']:.0e} cycles). Reference check only; no life"
            " estimate."
        )
    else:
        fNote = (
            f"Equivalent stress is above reference fatigue strength ({fd['fs']}"
            f" MPa at {fd['fcyc']:.0e} cycles). Reference check only; no life"
            " estimate."
        )

if have_life:
    yrs = lifeN / (365.0 * cpd)
    yrs_str = "more than 1000" if yrs > 1000 else f"{yrs:.2f}"
    st.metric(label="Fatigue Life (Cycles)", value=f"{lifeN:.2e}")
    st.metric(label="Service Life (Years)", value=f"{yrs_str} years")

if fNote:
    st.info(fNote)

flagged_names = [f[0] for f in flags if f[1]]
if not flagged_names:
    st.caption(
        "**Casting quality:** No defect flagged by screening rules (does not"
        " guarantee a sound casting)."
    )
else:
    st.warning(
        f"**Casting quality warning:** Screening rules flag:"
        f" {', '.join(flagged_names)}. Fatigue life calculations assume a sound"
        " casting."
    )

st.caption(f"**Material Caveat:** {fd['caveat']}")

st.markdown("---")
st.caption(
    "Estimates only. Sand mould, no gating losses (flow loss factor = 1), riser"
    " cools through side and top, riser & casting fill together."
)