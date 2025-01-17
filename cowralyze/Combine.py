import io, argparse, sys
import json

from Helpers import write_to_file


def combine_reduced_files(files, outfile):
    """Combine multiple _reduced.json files into one file"""
    combined = []
    for f in files:
        fl = f
        if isinstance(fl, io.TextIOWrapper):
            fl = f.name

        with open(fl, 'r') as file:
            if file.buffer.name == outfile:
                continue

            data = json.load(file)

            for element in data:
                combined.append(element)

    try:
        result = sorted(combined, key=lambda k: k['date'], reverse=False)
    except Exception as e:
        result = combined
        print('Error sorting in [combine] step: ')
        print(e)

    write_to_file(outfile, result, 'w')


if __name__ == "__main__":
    # !/usr/bin/env python3
    files = []
    if len(sys.argv) > 1:
        # use provided files to combine
        parser = argparse.ArgumentParser()
        parser.add_argument('file', type=argparse.FileType('r'), nargs='+')
        args = parser.parse_args()
        files = args.file

    outFile = 'reduced.json'
    combine_reduced_files(files, outFile)
