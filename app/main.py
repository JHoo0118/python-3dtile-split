import argparse
from service.tile_chunk_service import TileChunkService
from service.ifc_service import IfcService

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Process some arguments.")
    parser.add_argument('-i', '--input_path', type=str, help='input file path', required=False)
    parser.add_argument('-o', '--output_path', type=str, help='output file path', required=False)
    parser.add_argument('-s', '--split_size', type=int, help='split size', required=False)

    args = parser.parse_args()

    # input_glb_path = f"../{args.input_path}" if args.input_path is not None else "./app/102_160001_01.glb"
    # output_path = f"../{args.output_path}" if args.output_path is not None else "./app/outputs"
    input_glb_path = args.input_path if args.input_path is not None else "./app/102_160001_01.glb"
    output_path = args.output_path if args.output_path is not None else "./app/outputs"
    split_size = args.split_size if args.split_size is not None else 100

    input_path, base_file_name_with_ext = input_glb_path.rsplit('/', 1)
    base_filename, file_ext = base_file_name_with_ext.rsplit('.', 1)
    if file_ext == 'ifc':
        batch_table, batch_table_mapping, mesh_name_mapping = IfcService().ifc_to_glb(
          input_ifc_path=input_glb_path,
          output_dir=input_path,
          output_base_filename=base_filename
        )

        TileChunkService().split_model_by_nodes(
          input_glb_path=f"{input_path}/{base_filename}.glb",
          output_dir=output_path,
          split_size=split_size,
          batch_table=batch_table,
          batch_table_mapping=batch_table_mapping,
          mesh_name_mapping=mesh_name_mapping,
        )
    else:
        TileChunkService().split_model_by_nodes(
          input_glb_path=input_glb_path,
          output_dir=output_path,
          split_size=split_size,
        )

# from service.ifc_service import IfcService
# if __name__ == "__main__":
#     IfcService().ifc_to_glb(
#       input_glb_path='./test/Ifc2s3_Duplex_Electrical.ifc',
#       output_dir='./outputs',
#       output_base_filename='Ifc2s3_Duplex_Electrical'
#     )