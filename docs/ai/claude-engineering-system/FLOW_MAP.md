# Flow map
Intake -> immutable task -> (diagnosis where needed) -> PRD author -> independent PRD reviewer -> implementation -> peer review -> [publish on existing MR] -> specialists -> independent AC verification -> human review.
Read-only peer/TL/EM/design/release routes do not implement. Reviewer FAIL goes to the human author on MR-review tasks. On implementation tasks it returns to the developer within the three-attempt budget, invalidating old code evidence.
Each phase has actual status/receipt; console claims alone do not advance gates. READY_FOR_HUMAN_REVIEW is not merged, deployed or production verified.
