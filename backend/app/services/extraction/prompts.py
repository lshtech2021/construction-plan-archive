"""VLM prompt templates for construction plan extraction."""
from __future__ import annotations

TITLE_BLOCK_EXTRACTION_PROMPT = """You are analyzing a construction drawing title block.
Extract the following metadata from the title block visible in the image and return it as JSON.

Required fields (use null if not found):
- project_name: Full name of the project
- project_number: Project/job number
- client_name: Client or owner name
- sheet_number: Sheet number (e.g., A-101, S-201)
- sheet_title: Title or description of the sheet
- discipline_code: Discipline prefix code (e.g., A, S, M, E, P)
- revision_number: Current revision number or letter
- revision_date: Date of most recent revision
- issue_date: Original issue date
- drawn_by: Initials or name of drafter
- checked_by: Initials or name of checker
- firm_name: Name of the architectural or engineering firm
- scale: Drawing scale (e.g., 1/4"=1'-0")
- confidence: Your confidence level — "high", "medium", or "low"

Return only valid JSON with these exact field names. Return null for any field you cannot determine."""

DRAWING_DESCRIPTION_PROMPT = """You are analyzing a construction drawing sheet.
Provide a detailed description of this drawing for semantic search and retrieval purposes.
Use precise construction and architectural terminology.

Return a JSON object with these fields:
- description: A comprehensive 2-4 sentence description of what is shown
- drawing_type: Type of drawing (e.g., floor_plan, elevation, section, detail, schedule, diagram)
- building_system: Primary building system shown (e.g., structural, HVAC, electrical, plumbing, architectural)
- elements_shown: Array of specific elements visible (e.g., ["columns", "beams", "doors", "windows"])
- floor_or_area: Floor level or building area depicted (e.g., "Level 2", "Roof", "Typical Bay")
- notable_callouts: Array of important notes, dimensions, or specifications called out
- confidence: Your confidence level — "high", "medium", or "low"

Return only valid JSON with these exact field names."""

DISCIPLINE_CLASSIFICATION_PROMPT = """You are classifying a construction drawing sheet.
{metadata_context}

Analyze the drawing and classify it according to construction industry standards.

Return a JSON object with these fields:
- discipline: One of: architectural, structural, civil, mechanical, electrical, plumbing, fire_protection, landscape, interior_design, specifications, general, other, unknown
- sheet_type: One of: floor_plan, elevation, section, detail, schedule, diagram, reflected_ceiling_plan, site_plan, one_line_diagram, riser_diagram, cover_sheet, general_notes, other, unknown
- confidence: "high", "medium", or "low"
- reasoning: Brief explanation of your classification decision

Return only valid JSON with these exact field names."""

TABLE_EXTRACTION_PROMPT = """You are extracting tabular data from a construction drawing.
Find and extract any tables, schedules, or structured lists visible in the image.

Return a JSON object with these fields:
- title: Table or schedule title (null if not present)
- headers: Array of column header strings
- rows: Array of row objects, each with a "cells" array of cell value strings

If no table is found, return: {"title": null, "headers": [], "rows": []}

Return only valid JSON with these exact field names."""

FULL_PAGE_ANALYSIS_PROMPT = """You are performing a comprehensive analysis of a construction drawing sheet.
Analyze all aspects of this drawing and return a structured JSON response.

Return a JSON object with these fields:
- title_block: Object with project_name, project_number, client_name, sheet_number, sheet_title, discipline_code, revision_number, revision_date, issue_date, drawn_by, checked_by, firm_name, scale (all nullable strings)
- drawing_description: Object with description, drawing_type, building_system, elements_shown (array), floor_or_area, notable_callouts (array)
- discipline: One of: architectural, structural, civil, mechanical, electrical, plumbing, fire_protection, landscape, interior_design, specifications, general, other, unknown
- sheet_type: One of: floor_plan, elevation, section, detail, schedule, diagram, reflected_ceiling_plan, site_plan, one_line_diagram, riser_diagram, cover_sheet, general_notes, other, unknown
- notes_summary: Brief summary of any general notes or specifications
- schedules: Array of any tables/schedules found, each with title, headers, rows
- key_details: Array of the most important technical details or specifications
- confidence: Overall confidence — "high", "medium", or "low"

Return only valid JSON with these exact field names."""
