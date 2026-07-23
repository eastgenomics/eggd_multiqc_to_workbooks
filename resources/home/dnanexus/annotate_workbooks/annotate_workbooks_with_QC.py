import pandas as pd
import openpyxl
import argparse
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(process)d] %(levelname)s: %(message)s"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Annotate sample workbooks with QC metrics")
    parser.add_argument("--multiqc_folder", required=True,
                        help="Name of MultiQC folder under multiqc_inputs/")
    parser.add_argument("--reports_folder", required=True,
                        help="Name of reports folder under reports_inputs/")
    parser.add_argument("--intersect_folder", required=True,
                        help="Intersect folder name under intersected_beds/")
    parser.add_argument("--config", required=True,
                        help="Path to config file with cell name and location")
    parser.add_argument("--file_suffix", required=True,
                        help="string for customisable file suffix")
    parser.add_argument("--intersect_suffix", default=".intersect.bed",
                        help="suffix used to find intersected bed files")
    return parser.parse_args()


def annotate_workbook(sample_row, reports_path):
    """
    Write QC values into specific location of excel file

    Args:
        sample_row (df): row of combined qc dataframe
    """
    # get needed column from qc table row

    sample = sample_row["Sample"]
    try:
        coverage = round(
            sample_row[
                "custom_content_custom_coverage-250x"
                ], 1
            )
        coverage_string = f"{coverage}%"

        # The freeMix score is % contamination predicted
        # conversion to percentage is now calculated during multiqc
        contamination = round(
            (sample_row[
                "verifybamid-FREEMIX"
                ]), 3
            )
        contamination_string = f"{contamination}%"

        # number of mapped_passed reads is now divided by 1M during multiqc
        total_reads_M = round(
            (sample_row[
                "samtools_flagstat-mapped_passed"
                ]), 1
            )
        total_reads_M_string = f"{total_reads_M}"

        fold80 = round(sample_row["FOLD_80_BASE_PENALTY"], 1)
        fold80_string = f"{fold80}"

        insert_size = int(sample_row[
            "picard_insertsizemetrics-summed_median"
            ])
        insert_size_string = f"{insert_size} bp"

        try:
            # if doenst exist try sex check format
            sex_check = sample_row["matched"]
            sex_check_string = f"{sex_check}"
        except KeyError as err:
            logging.info(f"No sex check value {err}, looking for somalier")
            try:
                sex_check = sample_row["Match_Sexes"]
                sex_check_string = f"Somalier used. Sex match: {sex_check}"
            except KeyError as err:
                logging.warning(f"{err}: Column missing for {sample}; skipped")
                return
    except KeyError as err:
        logging.warning(f"{err}: Column missing for {sample}; skipped")
        return

    # get workbook corresponding to sample
    path = reports_path / (sample + ".xlsx")
    try:
        sample_workbook = openpyxl.load_workbook(path)
    except FileNotFoundError as err:
        raise FileNotFoundError(f"No workbook found for {sample}") from err

    worksheet = sample_workbook['summary']

    # lookup cell locations and add data to sheet
    cell_locations = config_file.get("cell_locations", {})

    worksheet[cell_locations["somalier_text"]] = "Sex Check"
    worksheet[cell_locations["250_coverage"]] = coverage_string
    worksheet[cell_locations["freemix"]] = contamination_string
    worksheet[cell_locations["M_reads"]] = total_reads_M_string
    worksheet[cell_locations["fold_80"]] = fold80_string
    worksheet[cell_locations["insert_size"]] = insert_size_string
    worksheet[cell_locations["somalier"]] = sex_check_string

    # save file
    new_path = sample + file_suffix
    sample_workbook.save(new_path)


def create_combined_qc(multiqc_path):
    """
    Create one large table of all relevant QC metrics
    Args:
        multiqc_path (Path): path to multiqc folder
    Returns:
        combined_qc (df): dataframe of relevant QC metrics
    """
    # get general statistics, picard hs metrics and somalier

    general_stats_path = multiqc_path / config_file.get(
        "multiqc_file_names", {}).get("general_stats_file")
    hsmetrics_path = multiqc_path / config_file.get(
        "multiqc_file_names", {}).get("hsmetrics_file")
    sexcheck_path = multiqc_path / config_file.get(
        "multiqc_file_names", {}).get("sexcheck_file")
    somalier_path = multiqc_path / config_file.get(
        "multiqc_file_names", {}).get("somalier_file")

    # try finding sex check data, if not produced try somalier
    try:
        sexcheck = pd.read_csv(sexcheck_path, sep="\t")
    except FileNotFoundError as e:
        logging.info(f"Sexcheck not found: {e.filename}, looking for somalier")
        try:
            # if sex check file does not exist, find somalier check
            sexcheck = pd.read_csv(somalier_path, sep="\t")
        except FileNotFoundError as e:
            logging.error(f"Required MultiQC file missing: {e.filename}")
            raise
    except pd.errors.ParserError as e:
        logging.error(f"Failed to parse MultiQC file: {e}")
        raise

    try:
        general_stats = pd.read_csv(general_stats_path, sep="\t")
        hsmetrics = pd.read_csv(hsmetrics_path, sep="\t")
    except FileNotFoundError as e:
        logging.error(f"Required MultiQC file missing: {e.filename}")
        raise
    except pd.errors.ParserError as e:
        logging.error(f"Failed to parse MultiQC file: {e}")
        raise

    # combine into one qc table
    hs_sexcheck = pd.merge(hsmetrics, sexcheck, on="Sample")
    combined_qc = pd.merge(general_stats, hs_sexcheck, on="Sample")

    return combined_qc


def create_variant_key(gene, variant):
    """
    Create a key for a gene and variant combination to match config

    Args:
        gene (str): gene name
        variant (str): variant name
    Returns:
        key (str): unique key for gene and variant
    """
    if not variant or variant == ".":
        return gene
    return f"{gene}-{variant}"


def get_min_depth_per_gene(intersect_path):
    """
    Parse intersected bed file to {gene: min_depth}, {gene: start, end}

    Args:
        intersect_path (Path): path to intersected bed file
    Returns:
        gene_depths (dict): {gene: min_depth}
        gene_pos (dict): {gene: start, end}
    """
    gene_depths = {}
    gene_pos = {}

    with open(intersect_path) as f:
        for line in f:
            fields = line.strip().split("\t")
            if len(fields) < 8:
                continue
            # this assumes output from bedtools intersect run with
            # -wa -wb mosdepth per base bed + target bed
            depth = int(fields[3])
            start = fields[5]
            end = fields[6]
            gene = fields[7]
            pos = fields[5]

            key = create_variant_key(gene, variant)

            if key not in gene_depths or depth < gene_depths[key]:
                gene_depths[key] = depth
                gene_pos[key] = (start, end)

    return gene_depths, gene_pos


def write_gene_depth_to_cell(worksheet, key, depth, start, end):
    """
    Find min depth for given gene and write it into the workbook

    Args:
        worksheet (openpyxl.Worksheet): worksheet to write to
        gene (str): gene name
        depth (int): minimum depth
        start (str): start position
        end (str): end position
    Returns:
        depth (int): minimum depth
        start (str): start position
        end (str): end position
    """
    gene_cells = config_file.get("cell_locations", {}).get(
        "gene_depths", {}).get(gene)
    if gene_cells is None:
        logging.warning(f"No cell locations configured for {gene}; skipped")
        return None, None

    worksheet[gene_cells["depth_text"]] = key

    length = int(end) - int(start)
    one_based_start = int(start) + 1

    if length > 1:
        pos = f"{one_based_start}-{end}"
    else:
        pos = f"{one_based_start}"

    worksheet[gene_cells["min_depth"]] = f"{pos}: {depth}x"

    return depth, start, end


def process_workbooks(intersect_file, file_suffix, intersect_suffix):
    """
    Load each workbook and annotate with minimum depth per gene
    Args:
        intersect_file (Path): path to intersected bed file
        file_suffix (str): suffix for annotated workbook
        intersect_suffix (str): suffix for intersected bed file
    """
    sample = intersect_file.name.replace(intersect_suffix, "")
    workbook_path = Path(sample + file_suffix)
    if not workbook_path.exists():
        logging.warning(f"No annotated workbook found at {workbook_path}")
        return

    gene_depths, gene_pos = get_min_depth_per_gene(intersect_file)
    if not gene_depths:
        logging.warning(f"No genes found for {intersect_file.name}")

    try:
        sample_workbook = openpyxl.load_workbook(workbook_path)
        worksheet = sample_workbook["summary"]

        for key, depth in gene_depths.items():
            start, end = gene_pos[key]
            depth_result, _, _ = write_gene_depth_to_cell(
                worksheet,
                key,
                depth=depth,
                start=start,
                end=end)
            if depth_result is None:
                logging.warning(f"Skipped {gene}: no cell location")
        sample_workbook.save(workbook_path)
    except (OSError, KeyError, ValueError) as e:
        raise RuntimeError(
            f"Error processing {intersect_file.name}"
        ) from e


def annotate_gene_depths(intersect_path, file_suffix):
    """
    Annotate all workbooks with min depth for genes in intersected bed files.
    Args:
        intersect_path (Path): path to directory for intersected bed files
        file_suffix (str): suffix for annotated workbook
        intersect_suffix (str): suffix for intersected bed file
    """
    intersect_path = Path(intersect_path)
    files = list(intersect_path.glob(f"*{intersect_suffix}"))
    if not files:
        if intersect_path.exists():
            contents = list(intersect_path.iterdir())
            raise FileNotFoundError(
                f"No intersected bed files found in {intersect_path}. "
                f"Directory contains: {contents}")
        else:
            raise FileNotFoundError(
                f"Directory does not exist: {intersect_path}")

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(
            process_workbooks, intersect_file, file_suffix, intersect_suffix)
            for intersect_file in files
        ]
        for f in futures:
            f.result()


def main():
    global config_file, file_suffix, intersect_suffix
    args = parse_args()

    multiqc_folder = args.multiqc_folder
    reports_folder = args.reports_folder
    intersect_folder = args.intersect_folder
    config = args.config
    file_suffix = args.file_suffix
    intersect_suffix = args.intersect_suffix

    # read config string into dict
    with open(config, "r") as f:
        config_file = json.load(f)

    logging.info(f"Config: {config_file}")

    # validate config
    cell_locations = config_file.get("cell_locations", {})
    multiqc_file_names = config_file.get("multiqc_file_names", {})

    required_cells = {
        "250_coverage", "freemix", "M_reads", "fold_80",
        "insert_size", "somalier", "somalier_text", "gene_depths"
    }
    required_multiqc_files = {
        "general_stats_file", "hsmetrics_file",
        "sexcheck_file", "somalier_file"
    }

    missing_cell_locations = [
        f"cell_locations.{key}" for key in required_cells
        if not cell_locations.get(key)]
    missing_file_names = [
        f"multiqc_file_names.{key}" for key in required_multiqc_files
        if not multiqc_file_names.get(key)]
    if missing_cell_locations or missing_file_names:
        missing = ', '.join(missing_cell_locations + missing_file_names)
        raise ValueError(f"Missing required config values: {missing}")

    # set paths
    multiqc_path = Path("multiqc_inputs") / multiqc_folder
    reports_path = Path("reports_inputs") / reports_folder
    intersect_path = Path("intersected_beds") / intersect_folder

    logging.info(f"MultiQC path: {multiqc_path}")
    logging.info(f"Reports path: {reports_path}")
    logging.info(f"Intersected beds path: {intersect_path}")

    logging.info("Beginning python")
    qc_table = create_combined_qc(multiqc_path)

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        logging.info(f"Using {os.cpu_count()} CPU cores")
        futures = [
            executor.submit(annotate_workbook, row, reports_path)
            for _, row in qc_table.iterrows()
        ]
        for f in futures:
            f.result()

    logging.info("Reports annotated with run QC")

    annotate_gene_depths(intersect_path, file_suffix)

    logging.info("Reports annotated with gene depths")


if __name__ == "__main__":
    main()
