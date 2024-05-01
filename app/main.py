import argparse
from service.tile_chunk_service import TileChunkService

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

    TileChunkService().split_model_by_nodes(
      input_glb_path=input_glb_path,
      output_dir=output_path,
      split_size=split_size,
    )