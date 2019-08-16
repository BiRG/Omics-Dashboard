#!/usr/bin/env python3
import argparse
from omics_dashboard_client import Session, Collection

parser = argparse.ArgumentParser(description='Replace a collection on the server.')
parser.add_argument('input_file', type=str,
                    help='File to post to the server.')
parser.add_argument('collection_id', type=int,
                    help='Collection id on the server to update.')
parser.add_argument('omics_url', type=str,
                    help='URL of the Omics Dashboard service.')
parser.add_argument('omics_auth_token', type=str,
                    help='Authorization token for the Omics Dashboard service.')
args = parser.parse_args()

session = Session(args.omics_url, auth_token=args.omics_auth_token)
collection = session.get(Collection, args.collection_id)
collection.select_local_file(args.input_file)
session.update(collection, True)


