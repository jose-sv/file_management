#!/usr/bin/env python3
'''Versioning and management of files'''
import hashlib
import argparse
import os
import sys
import json
import logging
from datetime import datetime
import readline  # used for nice input handling

BLOCK_SIZE = 65536  # The size of each read from the file


def calc_sum(file_name):
    '''load and read through the file in blocks to calculate hash'''
    file_hash = hashlib.sha256()  # Create the hash object
    with open(file_name, 'rb') as f:  # Open the file to read it's bytes
        fb = f.read(BLOCK_SIZE)  # Read from the file.
        while len(fb) > 0:  # While there is still data being read from the file
            file_hash.update(fb)  # Update the hash
            fb = f.read(BLOCK_SIZE)  # Read the next block from the file

    return file_hash.hexdigest()


def load_info(path):
    try:
        with open(f'{path}/{INFO_NAME}', 'rb') as info_file:
            data = json.load(info_file)
    except FileNotFoundError:  # backwards compatibility
        with open(f'{path}/.{INFO_NAME.split(".")[1]}', 'rb') as info_file:
            import pickle
            data = pickle.load(info_file)
            logging.warning("%s/%s is a pickle file, converting to json",
                            path, INFO_NAME)
        save_info(path, data)

    return data


def save_info(path, data_dict):
    with open(path + '.json', 'w') as save_file:
        # pickle.dump(data_dict, save_file, pickle.HIGHEST_PROTOCOL)
        json.dump(data_dict, save_file, indent=4)


INFO_NAME = '.file_info.json'


def find_info(opt):
    curr_dir = os.getcwd()
    max_parent = opt.max_parent or len(curr_dir.split('/'))
    upcount = 0
    while curr_dir != '/' and upcount < max_parent:
        print(curr_dir, upcount, max_parent)
        # give preference to json
        if os.path.exists(f'{curr_dir}/{INFO_NAME}'):
            return curr_dir
        # but check if pickle exists
        elif os.path.exists(f'{curr_dir}/.{INFO_NAME.split(".")[1]}'):
            return curr_dir
        else:
            # file not found, search parent directory
            curr_dir = '/'.join(curr_dir.split('/')[:-1])
            parent -= 1

    raise FileNotFoundError


def print_info(info_dict, file_name):
    name = info_dict['fname']
    if file_name is not None and file_name != name:
        name = f'{file_name} -> {name}'
    print(f"{name} ({info_dict['date']}):"
          f" {info_dict['note']}")


def process_single(file_info, add_policy, file_name=None, hash_val=None):
    assert(file_name is not None or hash_val is not None), 'missing name or ' \
                                                           'hash'

    # if explicitly adding/editing, skip print of original values
    if add_policy != 'add':
        try:
            # prefer hashval to file_name if both given (skip computation)
            if hash_val is None:
                search_res = file_info[calc_sum(file_name)]
            else:
                search_res = file_info[hash_val]
            name = None if file_name is None else file_name.split('/')[-1]
            print_info(search_res, name)
            return False, file_info

        except KeyError:  # search failed, add?
            missing = hash_val or file_name.split('/')[-1]
            if add_policy == 'skip':  # explicitly skipping; don't ask
                print(f'{missing} not found')
                return False, file_info

            if add_policy == 'ask':  # unclear, ask
                ans = input(f'{missing} not found in list, add? [Y/n]') or 'y'
                if ans.capitalize() != 'Y':
                    return False, file_info

    f_sum = hash_val or calc_sum(file_name)
    new_file = dict()
    new_file['date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    new_file['note'] = args.note or ""
    while new_file['note'] == "":
        try:
            new_file['note'] = input('Enter note: ')
            if new_file['note'] == "":
                logging.warning('Blank note not allowed')
        except KeyboardInterrupt:
            logging.info('Skipping')
            return False, file_info

    if file_name is not None:  # trim path
        file_name = file_name.split('/')[-1]
    # if hash given, prompt for file name
    new_file['fname'] = file_name or input('File name:')
    file_info[f_sum] = new_file

    return True, file_info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('fname', nargs='*', help='File to version')
    parser.add_argument('--hash', '-s', nargs='*', help='hash to search for')
    parser.add_argument('--max_parent', '-m', default=None, type=int)
    parser.add_argument('--add', '-a', action='store_true', help='Add or edit')
    parser.add_argument('--note', '-n', default='')
    parser.add_argument('--all', '-p', action='store_true')
    parser.add_argument('--no-add', '-o', action='store_true')
    args = parser.parse_args()

    FORMAT = '%(message)s [%(levelno)s-%(asctime)s %(module)s:%(funcName)s]'
    logging.basicConfig(level=logging.WARNING, format=FORMAT)

    changed = False  # conditional save

    try:
        load_path = find_info(args)
        info = load_info(load_path)
        if args.all:
            for f_hash in info:
                dat = info[f_hash]
                print_info(dat, None)

    except FileNotFoundError:
        try:
            ans = input(f'{INFO_NAME} not found, generate? [Y/n]') or 'y'
            if ans.capitalize() != 'Y':
                sys.exit()
        except KeyboardInterrupt:
            sys.exit()

        info = {}
        changed = True
        load_path = f'.'

    if args.fname is None:
        sys.exit()

    load_path = '/'.join([load_path, INFO_NAME])
    policy = 'skip' if args.no_add else 'add' if args.add else 'ask'
    for fname in args.fname:
        try:
            changed, info = process_single(info, policy, file_name=fname)
        except KeyboardInterrupt:
            sys.exit()

    if args.hash is not None:
        for h_val in args.hash:
            try:
                changed, info = process_single(info, policy, hash_val=h_val)
            except KeyboardInterrupt:
                sys.exit()

    if changed:
        save_info(load_path, info)
