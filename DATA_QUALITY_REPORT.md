# Vietnamese Culture Benchmark - Data Quality Report

**Generated**: 2025-12-07
**Author**: Automated Data Check

---

## Executive Summary

A comprehensive data quality check was performed on the Vietnamese Culture & Law Benchmark dataset. The following issues were identified and addressed:

### Issues Found and Fixed

| Issue Type | Status | Details |
|------------|--------|---------|
| Empty/Error ChatGPT answers (Culture) | **FIXED** | 9 answers regenerated via API |
| Empty/Error ChatGPT answers (Law) | **FIXED** | 2 answers regenerated via API |
| Missing ChatGPT answers (Culture) | **IN PROGRESS** | 1421 answers being generated (VH_1875-VH_3295) |

### Warnings (Not Critical)

| Warning Type | Count | Notes |
|--------------|-------|-------|
| Duplicate questions (Culture) | 3 groups (6 items) | Different answers from different source chunks |
| Duplicate questions (Law) | 16 groups (36 items) | Different answers from different source chunks |

---

## Detailed Analysis

### 1. Benchmark Files

#### Culture Benchmark (culture_benchmark.json)
- **Total items**: 3,295
- **Errors**: 0
- **Warnings**: 3 duplicate question groups
  - VH_957 & VH_1542: "Tai sao gia dinh duoc coi la yeu to quan trong..."
  - VH_1511 & VH_2632: "Khai niem 'khuc xa' trong van hoa..."
  - VH_1861 & VH_1966: "Giao duc co vai tro gi trong viec phat trien xa hoi?"

#### Law Benchmark (law_benchmark.json)
- **Total items**: 1,840
- **Errors**: 0
- **Warnings**: 16 duplicate question groups (36 items total)
  - Most common: "Phap luat duoc hieu la gi?" (5 occurrences)
  - Other duplicates include basic law concepts that appear in multiple chunks

### 2. ChatGPT Web Answers

#### Culture Answers (chatgpt_web_answers.json)
- **Before fix**: 1,874 answers (56.9% coverage)
  - 4 empty answers: VH_003, VH_006, VH_016, VH_149
  - 4 error answers: VH_014, VH_723, VH_727, VH_1460
  - 1 truncated answer: VH_148
- **After fix**: All 9 problematic answers regenerated
- **Missing**: 1,421 answers (VH_1875 to VH_3295) - being generated

#### Law Answers (chatgpt_web_answers_law.json)
- **Before fix**: 1,840 answers (100% coverage)
  - 1 error answer: PL_294
  - 1 truncated answer: PL_058
- **After fix**: Both answers regenerated
- **Status**: Complete (100% coverage)

### 3. Data Consistency

- **Cross-file consistency**: No issues found
- **ID sequence**: Continuous, no gaps
- **Source field format**: Consistent within each category
- **Category values**: All correct ("culture" or "law")

---

## Duplicate Questions Analysis

### Why duplicates exist?
The benchmark is generated from source PDF chunks. When similar topics appear in multiple chunks, similar questions may be generated. This is **not necessarily an error** - different answers may provide complementary information.

### Recommendation
For production use, consider:
1. **Keep all duplicates**: Provides multiple perspectives on the same topic
2. **Merge duplicates**: Combine answers for richer information
3. **Remove later duplicates**: Keep only the first occurrence

Currently, the duplicates are left as-is since they have different (but related) answers.

---

## Files Modified

### Fixed Answer Files
1. `chatgpt_web_answers.json` - 9 answers regenerated
2. `chatgpt_web_answers_law.json` - 2 answers regenerated

### Scripts Created
1. `data_generation/comprehensive_data_checker.py` - Full data validation
2. `data_generation/fix_missing_answers.py` - Fix empty/error answers
3. `data_generation/generate_missing_culture_answers.py` - Generate missing answers
4. `data_generation/analyze_duplicates.py` - Analyze duplicate questions

### Reports Generated
1. `data_check_report.json` - Detailed check results
2. `DATA_QUALITY_REPORT.md` - This summary report

---

## Next Steps

1. **Wait for missing answer generation to complete** (1,421 answers)
2. **Re-run validation** to confirm all issues resolved
3. **Optional**: Decide on duplicate question handling strategy
4. **Re-export Excel files** with updated data

---

## Statistics Summary

| Metric | Culture | Law | Total |
|--------|---------|-----|-------|
| Benchmark items | 3,295 | 1,840 | 5,135 |
| ChatGPT answers (after fix) | 1,874 + 1,421* | 1,840 | 5,135 |
| Duplicate groups | 3 | 16 | 19 |
| Critical errors | 0 | 0 | 0 |

*1,421 answers currently being generated
