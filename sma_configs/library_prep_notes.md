# SMA-seq Library Prep Notes
**Author:** Isaac Farnum
**Date:** 12/16/2025

---

## 11242025_IF_Part4_SMA_seq

**Targets:** V04.1-4.4, V0-39 through V0-47, V04.14-4.17
**Barcodes:** NB01-NB17 (17 barcodes)

| Step | Description |
|------|-------------|
| 1 | Plasmids cut with BsaI and purified with beads |
| 2 | Plasmids end repaired and purified with beads |
| 3 | Plasmids dA tailed and purified with beads |
| 4 | Plasmids barcoded with NB01-NB17 and purified with beads |
| 5 | Plasmids ligated to adapter (NA) and purified with beads |

**Volume loaded:** 0.84 µL (50 pmol)

---

## 11242025_IF_Part4_CIP_Treated_SMA_seq

**Targets:** V04.1-4.4, V0-39 through V0-47, V04.14-4.17
**Barcodes:** NB01-NB17 (17 barcodes)

| Step | Description |
|------|-------------|
| 1 | Plasmids cut with BsaI and purified with beads |
| 2 | Plasmids end repaired and purified with beads |
| 3 | Plasmids dA tailed and purified with beads |
| 4 | Plasmids barcoded with NB01-NB17 and purified with beads |
| 5 | Plasmids ligated to **CIP treated** adapter (NA) and purified with beads |

**Note:** CIP treatment killed helicase activity from using ethanol during purification.

**Volume loaded:** 0.81 µL (50 pmol)

---

## 12082025_IF_NewBCPart4_SMA_seq

**Targets:** V0-4.1, 4.2, 4.3, 4.4, V0-39
**Barcodes:** NB01-NB05 (5 barcodes, new barcode design)

| Step | Description |
|------|-------------|
| 1 | Plasmids cut with BsaI and purified with beads |
| 2 | 100 nM of each new barcode ligated to plasmids, purified with beads |
| 3 | Adapter ligated to plasmids and purified using beads |

**Volume loaded:** 1.1 µL (50 pmol)

---

## 12182025_IF_NewBC_Ex1_SMA_seq

**Targets:** V0-4.1, 4.2, 4.3, 4.4, V0-39
**Method:** Cleavage-ligation cycling (one tube)
**Barcode design:** Modified barcodes designed to upstream end of target sequence

| Step | Description |
|------|-------------|
| 1 | Plasmids cut with BsaI |
| 2 | Ligated to modified barcodes using Hi-T4 DNA Ligase |
| 3 | Ligated to adapter (NA) in one tube |

**Thermocycler Protocol:**
- Initial cleavage: 37°C for 10 min
- Cleavage/Ligation cycling: 37°C for 3 min → 16°C for 3 min (10 cycles)
- Final cleavage: 37°C for 15 min
- Purified using 2X volume beads

**Volume loaded:** 1.68 µL (50 fmol)

---

## 12182025_IF_NewBC_Ex2_SMA_seq

**Targets:** V0-4.1, 4.2, 4.3, 4.4, V0-39
**Method:** Cleavage-ligation cycling with Immobilized T4 DNA Ligase
**Barcode design:** Modified barcodes designed to **both ends** of target sequences

| Step | Description |
|------|-------------|
| 1 | Plasmids cut with BsaI |
| 2 | Ligated to modified barcodes with Immobilized T4 DNA Ligase |
| 3 | Ligated to adapter (NA) in one tube |

**Thermocycler Protocol:**
- Initial cleavage: 37°C for 10 min
- Cleavage/Ligation cycling: 37°C for 3 min → 16°C for 3 min (10 cycles)
- Tube removed from thermocycler
- Removed supernatant from beads using magnet
- Final cleavage on supernatant: 37°C for 15 min
- Purified using 2X volume beads

**Volume loaded:** 2.25 µL (50 fmol)

---

## 12182025_IF_NewBC_Ex3_SMA_seq

**Targets:** V0-4.1, 4.2, 4.3, 4.4, V0-39
**Method:** Cleavage-ligation cycling (separate tubes per plasmid)
**Barcode design:** Modified barcodes designed to **both ends** of target sequences

| Step | Description |
|------|-------------|
| 1 | Plasmids cut with BsaI |
| 2 | Ligated to modified barcodes |
| 3 | Ligated to adapter (NA) |
| 4 | Ligation cycling done in **separate tubes** (5 tubes) |
| 5 | All 5 tubes combined and purified using beads |

**Thermocycler Protocol:**
- Initial cleavage: 37°C for 10 min
- Cleavage/Ligation cycling: 37°C for 3 min → 16°C for 3 min (10 cycles)
- Final cleavage: 37°C for 15 min

**Volume loaded:** 2.2 µL (50 fmol)

---

## 12232025_IF_DoubleBC_SMA_seq

**Targets:** V0-4.1, 4.2, 4.3, 4.4, V0-39
**Method:** Double barcode cleavage-ligation cycling (one tube)
**Barcode design:** Modified barcodes designed to **both ends** of target sequences

| Step | Description |
|------|-------------|
| 1 | Plasmids cut with BsaI |
| 2 | Ligated to modified barcodes |
| 3 | Ligated to adapter (NA) in one tube |

**Thermocycler Protocol:**
- Initial cleavage: 37°C for 10 min
- Cleavage/Ligation cycling: 37°C for 3 min → 16°C for 3 min (10 cycles)
- Final cleavage: 37°C for 15 min

**Volume loaded:** 2.2 µL (50 fmol)

---

## Lessons Learned: New Barcode Experiments

### What Went Wrong
1. **Daisy chaining** - Much more daisy chaining observed
2. **Backbone attachment** - Barcodes with adapters seen attached to backbone

### Root Cause
The backbone left behind from **adjacent Level 0 plasmids** presents a perfect match for other barcodes.

### How to Fix
- Each SMA-seq experiment should include **only odd numbered** Level 0 plasmids OR **only even numbered** Level 0 plasmids
- Double barcoding Level 0 inserts will work if adjacent Level 0 plasmids in the golden gate scheme are not present

---

## Summary Table

| Experiment | Date | Barcodes | Targets | Method | Load Volume |
|------------|------|----------|---------|--------|-------------|
| 11242025_IF_Part4 | 11/24/25 | NB01-17 | 17 targets | Standard | 0.84 µL (50 pmol) |
| 11242025_IF_Part4_CIP | 11/24/25 | NB01-17 | 17 targets | CIP treated | 0.81 µL (50 pmol) |
| 12082025_IF_NewBCPart4 | 12/08/25 | NB01-05 | 5 targets | New BC | 1.1 µL (50 pmol) |
| 12182025_Ex1 | 12/18/25 | NB01-05 | 5 targets | Hi-T4, upstream | 1.68 µL (50 fmol) |
| 12182025_Ex2 | 12/18/25 | NB01-05 | 5 targets | Immob T4, both ends | 2.25 µL (50 fmol) |
| 12182025_Ex3 | 12/18/25 | NB01-05 | 5 targets | Separate tubes | 2.2 µL (50 fmol) |
| 12232025_DoubleBC | 12/23/25 | NB01-10 | 5 targets | Double BC | 2.2 µL (50 fmol) |
