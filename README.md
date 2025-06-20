# eggd_multiqc_to_workbooks

## What does this app do? ##

eggd_multiqc_to_workbooks finds the multiqc data txt files corresponding to the metrics that would be manually copied and pasted into the workbooks by scientists, and automatically adds the QC metrics into the correct cells.

Currently the app looks for:
- multiqc_general_stats.txt
- multiqc_picard_HsMetrics.txt
- multiqc_somalier_sex_check.txt

From these files the following metrics are found and added to the workbooks:
- % Coverage at 250 X
- FreeMix
- Total Reads (M)
- Fold 80 base penalty
- Insert size
- Somalier Sex Check

The tool also adds the text "Somalier" into cell A20 in the summary page of the workbook. Data is from somalier is added to B20, but currently the "Somalier text" is added manually by scientists when processing the workbooks.

## What data are required for this app to run? ##

**Required input files**

1. The following files should be held in the same folder (given with input `-ipath_to_multiqc_folder` )
    - multiqc_general_stats.txt
    - multiqc_picard_HsMetrics.txt
    - multiqc_somalier_sex_check.txt
2. An excel workbook files to annotate with qc metrics, held in the same folder (given with input `-ipath_to_reports_folder`)
3. A json file containing the cells to update (given with input `-iconfig_file`)

**Output files**

1. An annotated workbook file for each sample

**Example**

```
dx run eggd_multiqc_to_workbooks -ipath_to_multiqc_folder="project-J10ZQ3848Z9XJ9G77ZbGYbXZ:/output/test_locked/multiQC_data/" -ipath_to_reports_folder="project-J10ZQ3848Z9XJ9G77ZbGYbXZ:/output/test_locked/report_workbook/" -iconfig_file="file-J18290848Z9q6FzQF3jbF99v" --destination "project-J10ZQ3848Z9XJ9G77ZbGYbXZ:/output/test_locked/annotated_workbook"
```