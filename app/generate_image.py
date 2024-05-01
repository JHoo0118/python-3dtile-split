import argparse
from service.generate_image_service import GenerateImageService

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Process some arguments.")
    parser.add_argument('-i', '--input_path', type=str, help='input file path', required=False)
    parser.add_argument('-o', '--output_image_path', type=str, help='output image path', required=False)
    parser.add_argument('-lenses', '--camera_lenses', type=int, help='camera lenses length', required=False)
    parser.add_argument('-dist', '--camera_distance', type=float, help='camera distance', required=False)
    parser.add_argument('-hdir', '--horizontal_rotate_direction', type=str, help="If it's clockwise, cw If it's counterclockwise, type ccw.", required=False)
    parser.add_argument('-hdeg', '--horizontal_rotate_degree', type=float, help='horizontal rotate degree', required=False)
    parser.add_argument('-vdir', '--vertical_rotate_direction', type=str, help="If it's upward, u If it's downward, type d.", required=False)
    parser.add_argument('-vdeg', '--vertical_rotate_degree', type=float, help='vertical rotate degree', required=False)

    args = parser.parse_args()

    input_glb_path = args.input_path if args.input_path is not None else "./app/102_160001_01.glb"
    output_image_path = args.output_image_path if args.output_image_path is not None else "./app/outputs/102_160001_01.png"
    camera_lenses = args.camera_lenses if args.camera_lenses is not None else 30
    camera_distance = args.camera_distance if args.camera_distance is not None else 1.3
    horizontal_rotate_direction = args.horizontal_rotate_direction if args.horizontal_rotate_direction is not None else "cw"
    horizontal_rotate_degree = args.horizontal_rotate_degree if args.horizontal_rotate_degree is not None else "0"
    vertical_rotate_direction = args.vertical_rotate_direction if args.vertical_rotate_direction is not None else "u"
    vertical_rotate_degree = args.vertical_rotate_degree if args.vertical_rotate_degree is not None else "0"

    GenerateImageService().generate_image(
        input_glb_path=input_glb_path,
        output_image_path=output_image_path,
        camera_lenses=camera_lenses,
        camera_distance=camera_distance,
        horizontal_rotate_direction=horizontal_rotate_direction, 
        horizontal_rotate_degree=horizontal_rotate_degree,
        vertical_rotate_direction=vertical_rotate_direction,
        vertical_rotate_degree=vertical_rotate_degree
    )