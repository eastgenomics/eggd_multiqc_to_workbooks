import pandas as pd
import openpyxl
import sys

# create annotate excel table function
multiqc_folder=sys.argv[1]
reports_folder=sys.argv[2]
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
    sample_workbook = openpyxl.load_workbook(path)
    worksheet = sample_workbook['summary']

    # add "Somalier" to cell where data is currently added
    worksheet['A20'] = "Somalier"
    # add data to sheet
    worksheet['B15'] = coverage
    worksheet['B16'] = contamination
    worksheet['B17'] = total_reads_M
    worksheet['B18'] = fold80
    worksheet['B19'] = insert_size
    worksheet['B20'] = somalier

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