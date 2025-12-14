# Perth Urban Parks ODI Dataset — Summary

This dataset is derived from the study “Understanding Urban Park Use and Preferences: A Case Study of Perth, Western Australia” published in the MDPI Data journal.
Original publication: https://www.mdpi.com/2306-5729/3/4/69

# Overview

The dataset contains survey responses collected from 393 visitors to several urban parks in Perth, Australia.
Respondents were asked to rate 22 different park-related outcomes on:
	•	Importance (how important each amenity or outcome is)
	•	Satisfaction (how well their local park currently delivers it)

These outcomes include amenities such as shade, seating, lighting, dog exercise areas, cleanliness, maintenance, and nature-related experiences.

# Why This Dataset Is Included

This dataset is included as an example for demonstrating Juno’s full ODI workflow because:
    - It is real-world data from a published academic study.
	- It contains a diverse population with different park usage patterns.
	- It includes a broad set of outcome statements across a shared job-to-be-done.
	- It produces interpretable need-based segments, such as “Active Dog Owners” and “Nature-Enjoying Seniors.”

The dataset serves as a practical, domain-neutral reference for testing Juno’s segmentation pipeline.

# Data Cleaning Notes

The dataset has been lightly pre-processed for use with Juno:
    - Pivoted from wide to long format, with one record per respondent–outcome pair.
    - Importance and satisfaction values were rounded to the nearest integer to ensure clean 1–5 scale ratings.
	- No other cleaning or transformations were performed.

Juno itself does not perform any data cleaning. It requires strictly formatted, pre-cleaned input data and assumes all values are valid as provided.

# Licensing & Attribution

The original dataset is published under the Creative Commons Attribution (CC BY) license, which allows redistribution and adaptation with proper citation.

Please cite the authors as required:

Roberts, A.; Thompson, S.M.; Pawley, M.; Page, S.; Whyte, D.
Understanding Urban Park Use and Preferences: A Case Study of Perth, Western Australia.
Data 2018, 3(4), 69.