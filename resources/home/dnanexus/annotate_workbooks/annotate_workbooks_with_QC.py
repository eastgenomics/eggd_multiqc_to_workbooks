import pandas as pd
import openpyxl
import sys
import json

# create annotate excel table function
multiqc_folder=sys.argv[1]
reports_folder=sys.argv[2]
config_json = sys.argv[3]
print(config_json)
cells_to_edit=json.loads(config_json)

multiqc_path = "multiqc_inputs/" + multiqc_folder + "/"
reports_path = "reports_inputs/" + reports_folder + "/"

def annotate_workbook(sample_row, reports_path):
    """
    Write QC values into specific location of excel file

    Args:
        sample_row (df): row of combined qc dataframe
    """
    # get needed column from qc table row
    sample = sample_row["Sample"]
    coverage = sample_row["custom_coverage_mqc-generalstats-custom_coverage-250x"]
    contamination = sample_row["VerifyBAMID_mqc-generalstats-verifybamid-FREEMIX"]
    total_reads_M = sample_row["Samtools_mqc-generalstats-samtools-mapped_passed"]
    fold80 = sample_row["FOLD_80_BASE_PENALTY"]
    insert_size = sample_row["Picard_mqc-generalstats-picard-summed_median"]
    somalier = sample_row["Match_Sexes"]

    # get workbook corresponding to sample
    print(sample)
    path = reports_path + sample + ".xlsx"
    try:
        sample_workbook = openpyxl.load_workbook(path)
    except FileNotFoundError:
        # doesn't exist
        print("No workbook found for ", sample)
        return

    # sample_workbook = openpyxl.load_workbook(path)
    worksheet = sample_workbook['summary']

    # add data to sheet
    # want to pass cell locations in via a config for customisation
    worksheet[cells_to_edit.get("250_coverage")] = coverage
    worksheet[cells_to_edit.get("freemix")] = contamination
    worksheet[cells_to_edit.get("M_reads")] = total_reads_M
    worksheet[cells_to_edit.get("fold_80")] = fold80
    worksheet[cells_to_edit.get("insert_size")] = insert_size
    worksheet[cells_to_edit.get("somalier")] = somalier

    # save file
    new_path= sample + "_QC_added.xlsx"
    sample_workbook.save(new_path)

def create_combined_qc(multiqc_path):
    """
    Create one large table of all relevant QC metrics
    """
    # get general statistics, picard hs metrics and somalier

    general_stats_path = multiqc_path + "multiqc_general_stats.txt"
    hsmetrics_path = multiqc_path + "multiqc_picard_HsMetrics.txt"
    somalier_path = multiqc_path + "multiqc_somalier_sex_check.txt"

    general_stats = pd.read_csv(general_stats_path, sep="\t")
    hsmetrics= pd.read_csv(hsmetrics_path, sep="\t")
    somalier= pd.read_csv(somalier_path, sep="\t")

    # combine into one qc table
    hs_somalier = pd.merge(hsmetrics, somalier, on="Sample")
    combined_qc = pd.merge(general_stats, hs_somalier, on="Sample")

    return combined_qc


print("Beginning python")
qc_table = create_combined_qc(multiqc_path)
qc_table.apply(annotate_workbook, axis=1, reports_path = reports_path)

print("Reports annotated")

# to make an app would need to have path to MultiQC output, or just work folder
# need to have path to reports
# fix sample names
# need to transform coverage to %
# need to make total reads human readable
# need to makr fold80 fewer sigfig
# need to ad bp to insert size

# apply annotate function to all samples in big qc table