"""
This script is intended to wake up every 30 min or so (eg via cron),
it checks for any new arxiv papers via the arxiv API and stashes
them into a sqlite database.
"""

import sys
import time
import random
import logging
import argparse

from aslite.arxiv import get_response, parse_response
from aslite.db import get_papers_db, get_metas_db

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='%(name)s %(levelname)s %(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    parser = argparse.ArgumentParser(description='Arxiv Daemon')
    parser.add_argument('-n', '--num', type=int, default=100, help='how many papers to fetch')
    parser.add_argument('-s', '--start', type=int, default=0, help='start at what index')
    args = parser.parse_args()
    print(args)

    # query string of papers to look for
    q = 'cat:cs.CV+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.AI+OR+cat:cs.NE+OR+cat:cs.RO'

    pdb = get_papers_db(flag='c')
    mdb = get_metas_db(flag='c')
    prevn = len(pdb)

    def store(p):
        pdb[p['_id']] = p
        mdb[p['_id']] = {'_time': p['_time']}

    # fetch the latest papers
    for k in range(args.start, args.start + args.num, 100):
        logging.info('querying arxiv api for query %s at start_index %d' % (q, k))

        # attempt to fetch a batch of papers from arxiv api
        ntried = 0
        while True:
            try:
                resp = get_response(search_query=q, start_index=k)
                papers = parse_response(resp)
                time.sleep(0.5)
                if len(papers) == 100:
                    break # otherwise we have to try again
            except Exception as e:
                logging.warning(e)
                logging.warning("will try again in a bit...")
                ntried += 1
                if ntried > 1000:
                    logging.error("ok we tried 1,000 times, something is srsly wrong. exitting.")
                    sys.exit()
                time.sleep(2 + random.uniform(0, 4))

        # process the batch of retrieved papers
        nhad, nnew, nreplace = 0, 0, 0
        for p in papers:
            pid = p['_id']
            if pid in pdb:
                if p['_time'] > pdb[pid]['_time']:
                    # replace, this one is newer
                    store(p)
                    nreplace += 1
                else:
                    # we already had this paper, nothing to do
                    nhad += 1
            else:
                # new, simple store into database
                store(p)
                nnew += 1
        prevn = len(pdb)

        # some diagnostic information on how things are coming along
        logging.info(papers[0]['_time_str'])
        logging.info("k=%d, out of %d: had %d, replaced %d, new %d. now have: %d" %
             (k, len(papers), nhad, nreplace, nnew, prevn))

        # zzz
        time.sleep(1 + random.uniform(0, 3))
