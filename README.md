# eggd_multiqc_to_workbooks

## What does this app do? ##

eggd_multiqc_to_workbooks finds the multiqc data txt files corresponding to the metrics that would be manually copied and pasted into the workbooks by scientists, and automatically adds the QC metrics into the correct cells.

Currently the app looks for:
- multiqc_general_stats.txt
- multiqc_picard_HsMetrics.txt
- multiqc_multiqc_sex_check_table.txt, if unavailable then multiqc_somalier_sex_check.txt

From these files the following metrics are found and added to the workbooks:
- % Coverage at 250 X
- FreeMix
- Total Reads (M)
- Fold 80 base penalty
- Insert size
- Sex Check or Somalier Sex Check

The tool also adds the text "Sex Check" in the summary page of the workbook to the cell specified by the config file. This is done as  currently the text "Somalier" is added manually by scientists when processing the workbooks, but the lab will move to using the tool Sex Check in the next release.

If the data from the tool eggd_sex_check is available, this is added to cell specified in the config file. If Unavailable, but data from somalier is available, the output od somalier will be added with the text "Somalier used. Sex match:". Data is from somalier is added to B20, but currently the "Somalier text" is added manually by scientists when processing the workbooks.

## What data are required for this app to run? ##

**Required input files**

1. The following files should be held in the same folder (given with input `-ipath_to_multiqc_folder` )
    - multiqc_general_stats.txt
    - multiqc_picard_HsMetrics.txt
    - multiqc_multiqc_sex_check_table.txt or multiqc_somalier_sex_check.txt
2. An excel workbook files to annotate with qc metrics, held in the same folder (given with input `-ipath_to_reports_folder`)
3. A json file containing the cells to update (given with input `-iconfig_file`)

**Optional inputs**

1. A file suffix for the output file, default = ".xlsx" (given with input `-ifile_suffix`)

**Output files**

1. An annotated workbook file for each sample

**Example**

```
dx run eggd_multiqc_to_workbooks \
 -ipath_to_multiqc_folder="project-J1BXZx04383J0pXJqgx3p9BY:/output/MYE-250612_1500/eggd_MultiQC/250611_A01295_0544_BH3CKYDRX7_MYE-MYE-250612_1500-multiqc_data/" \
 -ipath_to_reports_folder="project-J1BXZx04383J0pXJqgx3p9BY:/output/MYE-250612_1500/eggd_generate_variant_workbook-2.10.1/" \
 -iconfig_file="file-J1BXbb84383BYV07QJ8FV4q6" \
 --destination "project-J1BXZx04383J0pXJqgx3p9BY:/output/MYE-250612_1500/eggd_multiqc_to_workbooks-1.0.0"
```