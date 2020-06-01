'''Versioning and management of files'''
import pickle
import hashlib
import argparse
import os
import sys
import json
import logging
from datetime import datetime
import readline  # used for nice input handling

BLOCK_SIZE = 65536  # The size of each read from the file


def calc_sum(fname):
    '''load and read through the file in blocks to calculate hash'''
    file_hash = hashlib.sha256()  # Create the hash object
    with open(fname, 'rb') as f:  # Open the file to read it's bytes
        fb = f.read(BLOCK_SIZE)  # Read from the file.
        while len(fb) > 0:  # While there is still data being read from the file
            file_hash.update(fb)  # Update the hash
            fb = f.read(BLOCK_SIZE)  # Read the next block from the file

    return file_hash.hexdigest()


def load_info(path):
    try:
        with open(f'{path}/{INFO_NAME}.json', 'rb') as info_file:
            data = json.load(info_file)
    except FileNotFoundError:  # backwards compatibility
        with open(f'{path}/{INFO_NAME}', 'rb') as info_file:
            data = pickle.load(info_file)
        logging.warning("%s/%s is a pickle file, converting to json",
                        path, INFO_NAME)
        save_info(path, data)

    return data


def save_info(path, data_dict):
    with open(path + '.json', 'w') as save_file:
        # pickle.dump(data_dict, save_file, pickle.HIGHEST_PROTOCOL)
        json.dump(data_dict, save_file, indent=4)


INFO_NAME = '.file_info'


def find_info(opt):
    curr_dir = os.getcwd()
    parent = len(curr_dir.split('/'))
    while curr_dir != '/' and parent > opt.max_parent:
        if os.path.exists(f'{curr_dir}/{INFO_NAME}'):
            return curr_dir
        else:
            # file not found, search parent directory
            curr_dir = '/'.join(curr_dir.split('/')[:-1])
            parent -= 1

    raise FileNotFoundError


def print_info(info_dict):
    print(f"{info_dict['fname']} ({info_dict['date']}):"
          f" {info_dict['note']}")


def process_single(fname, info):
    if not args.add:  # quit if found
        try:
            search_res = info[calc_sum(fname)]
            print_info(search_res)
            return info
        except KeyError:  # search failed, add?
            ans = input(f'{fname} not found in list, add? [Y/n]') or 'y'
            if ans.capitalize() != 'Y':
                return info

    f_sum = calc_sum(fname)
    if f_sum in info:
        print_info(info[f_sum])
    new_file = dict()
    new_file['date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        new_file['note'] = args.note or input('Enter note: ')
    except KeyboardInterrupt:
        logging.info('Caught kb interrupt, skipping')
        return info
    while new_file['note'] == "":
        logging.warning('Blank note not allowed')
        try:
            new_file['note'] = args.note or input('Enter note: ')
        except KeyboardInterrupt:
            logging.info('Caught kb interrupt, skipping')
            return info

    new_file['fname'] = fname
    info[f_sum] = new_file

    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('fname', nargs='*', help='File to version')
    parser.add_argument('--max_parent', '-m', default=-1)
    parser.add_argument('--add', '-a', action='store_true', help='Add or edit')
    parser.add_argument('--note', '-n', default='')
    parser.add_argument('--all', '-p', action='store_true')
    args = parser.parse_args()

    FORMAT = '%(message)s [%(levelno)s-%(asctime)s %(module)s:%(funcName)s]'
    logging.basicConfig(level=logging.WARNING, format=FORMAT)

    try:
        load_path = find_info(args)
        info = load_info(load_path)
        if args.all:
            for f_hash in info:
                dat = info[f_hash]
                print_info(dat)

    except FileNotFoundError:
        ans = input(f'{INFO_NAME} not found, generate? [Y/n]') or 'y'
        if ans.capitalize() != 'Y':
            sys.exit()

        info = {}
        load_path = f'.'

    if args.fname is None:
        sys.exit()

    load_path = '/'.join([load_path, INFO_NAME])
    for fname in args.fname:
        info = process_single(fname, info)

    save_info(load_path, info)
