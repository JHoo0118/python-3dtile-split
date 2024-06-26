import argparse
from service.ifc_service import IfcService

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Process some arguments.")
    parser.add_argument('-i', '--input_path', type=str, help='input file path', required=False)
    parser.add_argument('-o', '--output_path', type=str, help='output file path', required=False)
    parser.add_argument('-m', '--merge_metadata', type=str, help='merge metadata', required=False)

    args = parser.parse_args()

    input_ifc_path = args.input_path if args.input_path is not None else "./app/102_160001_01.ifc"
    output_path = args.output_path if args.output_path is not None else "./app/outputs"
    merge_metadata = args.merge_metadata == "true" if args.merge_metadata is not None else False

    input_path, base_file_name_with_ext = input_ifc_path.rsplit('/', 1)
    base_filename, file_ext = base_file_name_with_ext.rsplit('.', 1)
    batch_table, batch_table_mapping, mesh_name_mapping = IfcService().ifc_to_glb(
      input_ifc_path=input_ifc_path,
      output_dir=input_path,
      output_base_filename=base_filename
    )

    if merge_metadata:
        IfcService().merge_metadata(
            output_dir=input_path,
            base_name=base_filename
        )