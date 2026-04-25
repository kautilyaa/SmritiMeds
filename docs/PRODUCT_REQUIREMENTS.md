# SmritiMeds Product Requirements

## Purpose
I want SmritiMeds to turn medication labels and medical documents into understandable, editable reminders with explicit confidence and manual-review boundaries.

## Primary users
I am deliberately designing this product first for:
- patients managing recurring medication schedules
- caregivers managing reminders for another person
- operators reviewing medication instructions from documents

## Core user goals
The core goals I want this product to satisfy are:
1. upload a medication source and extract relevant instructions
2. convert extracted instructions into structured reminders
3. edit and manage reminders without re-running analysis
4. understand when output is uncertain and requires manual review

## Functional requirements

### Analysis intake
- accept bottle labels, blister packs, printed medical documents, and handwritten prescriptions
- support explicit routing modes plus an auto-routing mode
- allow an optional pill verification image

### Instruction extraction
- extract medication name, strength, raw instructions, and a structured schedule when possible
- preserve confidence notes and manual-review flags
- show fallback behavior when OCR is unavailable or low quality

### Reminder management
- import suggested reminders from analysis results
- create manual reminders
- edit reminder title, medication name, dose, time of day, exact reminder time, and notes
- toggle active/paused state
- mark reminders complete
- delete reminders
- clear completed reminders
- persist reminder state locally in the web application

### Operational transparency
- expose health and readiness information for OCR and local vision paths
- surface when local experimental models are unavailable or degraded

## Non-goals
I do not want SmritiMeds to position itself as:
- diagnosis
- prescribing treatment
- replacing pharmacist or clinician review
- guaranteeing OCR correctness
- guaranteeing pill identity

## Quality requirements
- responsive layout across desktop and smaller screens
- readable overflow behavior for long extracted text
- stable fallback path when OCR models fail
- low-friction local setup for development

## Current constraints
The constraints I am actively working within right now are:
- local OCR and local pill-classification quality depends on third-party model compatibility
- reminder persistence is browser-local, not multi-user or synced
- experimental local vision remains optional and non-authoritative
