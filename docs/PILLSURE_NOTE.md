# PillSure-inspired Safety Note

## Source
Shanthakumar P, Divyadharshini T, Muzzammil AM, Nandhini S, Varshini AN.  
**PillSure: A Dual-Modal Spectral And Imaging Framework For Tablet Authentication.**  
*International Journal of Drug Delivery Technology*. **2026**;16(12s):537-545.  
DOI: `10.25258/ijddt.16.12s.65`

Primary sources:
- Abstract page: https://ijddt.com/abstract/16/IJDDT%2CVol16%2CIssue12s%2CArticle65.html
- PDF: https://impactfactor.org/PDF/IJDDT/16/IJDDT%2CVol16%2CIssue12s%2CArticle65.pdf

## Important date note
The currently accessible journal pages cite the paper as **2026**, not early 2025, so that is the date I am using in my notes.

## Why it matters to SmritiMeds
The paper’s central premise is directly relevant to how I want SmritiMeds to behave as a serious product:

- visual analysis is useful for **surface inspection**
- chemical spectroscopy provides an independent **authenticity signal**
- relying on a visual model alone is unsafe because tablets can be:
  - worn
  - degraded
  - contaminated
  - visually imitated by counterfeit products

## What SmritiMeds adopted

Here is what I took from the paper and translated into the product direction.

### 1. Visual-only confidence penalty
The local pill pipeline now applies an explicit penalty because the local path has:
- visual evidence only
- no chemical spectroscopy

### 2. Scope-limited authentication language
The local vision result is described as:
- **visual surface only**
- supportive evidence
- not proof of chemical authenticity

### 3. Structured safety messaging
The UI surfaces:
- a visual-only confidence penalty
- adjusted visual confidence
- a structural-surface-only disclaimer
- risk factors that explain why the result remains uncertain

## Practical product implication
From a product-positioning standpoint, I believe SmritiMeds can credibly support:
- pill surface inspection
- coarse visual consistency checks
- reminder workflows

I do not want SmritiMeds to claim:
- chemical authentication
- counterfeit detection certainty
- pharmacy-grade identity verification

without an independent chemical modality.
