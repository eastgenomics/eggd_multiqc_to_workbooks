# eggd_qc_to_workbooks

## What does this app do? ##

eggd_qc_to_workbooks finds the multiqc and mosdepth data files corresponding to the metrics that would be manually copied and pasted into the workbooks by scientists, and automatically adds the QC metrics into the correct cells.

Currently the app looks for:
- multiqc_general_stats.txt
- multiqc_picard_HsMetrics.txt
- multiqc_sex_check_table.txt, if unavailable then multiqc_somalier_sex_check.txt
- <sample>_markdup.per-base.bed.gz

From these files the following metrics are found and added to the workbooks:
- % Coverage at 250 X
- FreeMix
- Total Reads (M)
- Fold 80 base penalty
- Insert size
- Sex Check or Somalier Sex Check
- Per gene Depth

The tool also adds the text "Sex Check" in the summary page of the workbook to the cell specified by the config file. This is done as  currently the text "Somalier" is added manually by scientists when processing the workbooks, but the lab will move to using the tool Sex Check in the next release.

If the data from the tool eggd_sex_check is available, this is added to cell specified in the config file. If Unavailable, but data from somalier is available, the output of somalier will be added with the text "Somalier used. Sex match:". Data is from somalier is added to B20, but currently the "Somalier text" is added manually by scientists when processing the workbooks.

## What data are required for this app to run? ##

**Required inputs**

1. MultiQC txt data files, from the `multiqc_data` folder of eggd_MultiQC (given with `-imultiqc_files`, array:file). These must include:
    - multiqc_general_stats.txt
    - multiqc_picard_HsMetrics.txt
    - multiqc_sex_check_table.txt or multiqc_somalier_sex_check.txt

    Other MultiQC txt files can be passed and are ignored.
2. Excel workbooks to annotate with QC metrics, one per sample, named `<sample>.xlsx` (given with `-ireports`, array:file)
3. Per-sample mosdepth per-base files, named `<sample>_markdup.per-base.bed.gz` (given with `-imosdepth_files`, array:file). Other mosdepth outputs are ignored.
4. A reference BED file containing genomic locations for which depth metrics are required (given with `-ipath_to_bedfile`)
5. A JSON config file containing the cells to update (given with `-iconfig_file`)

**Optional inputs**

1. A file suffix for the output file, default = ".xlsx" (given with `-ifile_suffix`)

**Output files**

1. An annotated workbook file for each sample

**Input names changed in v1.1.1**

The folder path inputs were replaced with file array inputs so the app can be run by eggd_conductor:

| v1.1.0 (folder path, string) | v1.1.1 (array:file) |
|---|---|
| `-ipath_to_multiqc_folder` | `-imultiqc_files` |
| `-ipath_to_reports_folder` | `-ireports` |
| `-ipath_to_mosdepth_folder` | `-imosdepth_files` |

**Example**

```
PROJECT=project-xxxx
RUN=/output/<run_name>

dx run eggd_qc_to_workbooks \
  $(dx find data --path "$PROJECT:$RUN/eggd_MultiQC/multiqc_data/" --name "*.txt" --brief | sed 's/^/-imultiqc_files=/') \
  $(dx find data --path "$PROJECT:$RUN/eggd_generate_variant_workbook-2.11.1/" --name "*.xlsx" --brief | sed 's/^/-ireports=/') \
  $(dx find data --path "$PROJECT:$RUN/eggd_mosdepth-1.1.0/" --name "*_markdup.per-base.bed.gz" --brief | sed 's/^/-imosdepth_files=/') \
  -ipath_to_bedfile="project-Fkb6Gkj433GVVvj73J7x8KbV:file-J9VZ1J04GYpqYJfj4QG2F9jB" \
  -iconfig_file="project-Fkb6Gkj433GVVvj73J7x8KbV:file-J9V2q084GYpfgv0XkXf10jjX" \
  --destination "$PROJECT:$RUN/eggd_qc_to_workbooks-1.1.1"
```
